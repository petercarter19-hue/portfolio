/* Proposed PS-RESUME-IDENTITY-001 rollback. Refuse any pinned history;
never erase a selected identity or reinterpret a retained publication. */
SET NOCOUNT ON;
SET XACT_ABORT ON;
BEGIN TRY
    BEGIN TRANSACTION;
    IF EXISTS(SELECT 1 FROM dbo.resume_media_placements WITH(UPDLOCK,HOLDLOCK)
              WHERE source_kind=N'generated_illustration')
        THROW 54310,'Rollback refused: catalog media placements exist.',1;
    IF COL_LENGTH(N'dbo.resume_media_command_receipts',N'catalog_source_bound') IS NOT NULL
        EXEC sys.sp_executesql N'IF EXISTS(SELECT 1 FROM dbo.resume_media_command_receipts WITH(UPDLOCK,HOLDLOCK) WHERE catalog_source_bound=1) THROW 54310, ''Rollback refused: catalog media command history exists.'',1;';
    IF COL_LENGTH(N'dbo.resume_publication_revisions',N'profile_identity_json') IS NOT NULL
        EXEC sys.sp_executesql N'IF EXISTS (SELECT 1 FROM dbo.resume_publication_revisions WITH (UPDLOCK,HOLDLOCK) WHERE profile_identity_json IS NOT NULL) THROW 54310, ''Rollback refused: pinned identity history exists.'', 1;';
IF EXISTS(SELECT 1 FROM dbo.resume_publication_outbox WITH(UPDLOCK,HOLDLOCK) WHERE event_type=N'publish' AND JSON_QUERY(payload_json,'$.candidate') IS NOT NULL) THROW 54310, 'Rollback refused: integrated publication history exists.', 1;
IF EXISTS(SELECT 1 FROM dbo.resume_draft_command_receipts WITH(UPDLOCK,HOLDLOCK) WHERE command_type IN(N'bind_story',N'clear_story')) OR EXISTS(SELECT 1 FROM dbo.resume_draft_items WITH(UPDLOCK,HOLDLOCK) WHERE record_type=N'knowledge') THROW 54310,'Rollback refused: personal entry draft history exists.',1;

    EXEC sys.sp_executesql N'CREATE OR ALTER PROCEDURE dbo.usp_CommitResumeMediaCommandForOwner
    @UserKey nvarchar(300),
    @RequestId uniqueidentifier,
    @CommandJson nvarchar(max)
AS
BEGIN
    SET NOCOUNT ON;
    SET XACT_ABORT ON;
    SET TRANSACTION ISOLATION LEVEL SERIALIZABLE;
    DECLARE @OwnTransaction bit = 0;
    IF @@TRANCOUNT = 0
    BEGIN
        BEGIN TRANSACTION;
        SET @OwnTransaction = 1;
    END;
    DECLARE @ProfileId bigint;
    SELECT @ProfileId = profile.profile_id
      FROM dbo.member_profiles AS profile WITH (UPDLOCK, HOLDLOCK)
      JOIN dbo.app_users AS app_user ON app_user.id = profile.user_id
     WHERE app_user.user_key = @UserKey AND app_user.active = 1 AND profile.active = 1;
    IF @ProfileId IS NULL
        THROW 52302, ''RESUME_MEDIA_NOT_FOUND'', 1;
    EXEC dbo.usp_ResumePublicationGuardLegacyMutator
        @ProfileId = @ProfileId, @Mutator = N''media'', @CommandJson = @CommandJson;
    EXEC dbo.usp_CommitResumeMediaCommandForOwnerCore
        @UserKey = @UserKey, @RequestId = @RequestId, @CommandJson = @CommandJson;
    IF @OwnTransaction = 1 COMMIT TRANSACTION;
END;';

    EXEC sys.sp_executesql N'CREATE OR ALTER PROCEDURE dbo.usp_GetResumeDraftForOwner
            @UserKey nvarchar(300)
        AS
        BEGIN
            SET NOCOUNT ON;
            SET XACT_ABORT ON;
            SET TRANSACTION ISOLATION LEVEL SERIALIZABLE;

            /* db.py uses an autocommit connection. Own the transaction inside
               the procedure so the two result sets are one consistent read
               and every lock is released by this procedure. */
            BEGIN TRY
            BEGIN TRANSACTION;

            DECLARE @ProfileId bigint;
            SELECT @ProfileId = profile.profile_id
            FROM dbo.member_profiles AS profile WITH (UPDLOCK, HOLDLOCK)
            JOIN dbo.app_users AS app_user ON app_user.id = profile.user_id
            WHERE app_user.user_key = @UserKey
              AND app_user.active = 1
              AND profile.active = 1;

            IF @ProfileId IS NULL
                THROW 52202, ''RESUME_DRAFT_NOT_FOUND'', 1;

            /* Fix the shared-resource lock order explicitly: owner draft,
               receipt range, then items. Keep the public reader at exactly two
               result sets by carrying receipts in the header JSON column. */
            DECLARE @ReadDraftId bigint;
            DECLARE @ReadDraftVersion int;
            DECLARE @ReadBasePublicationVersion nvarchar(64);
            SELECT @ReadDraftId = draft.resume_draft_id,
                   @ReadDraftVersion = draft.draft_version,
                   @ReadBasePublicationVersion = draft.base_publication_version
            FROM dbo.resume_drafts AS draft WITH (UPDLOCK, HOLDLOCK)
            WHERE draft.owner_profile_id = @ProfileId;

            DECLARE @CommandReceiptsJson nvarchar(max);
            SELECT @CommandReceiptsJson = (
                SELECT
                    CONVERT(nvarchar(36), receipt.request_id) AS request_id,
                    receipt.request_digest,
                    receipt.outcome
                FROM dbo.resume_draft_command_receipts AS receipt WITH (UPDLOCK, HOLDLOCK)
                WHERE receipt.owner_profile_id = @ProfileId
                ORDER BY receipt.committed_at_utc, receipt.request_id
                FOR JSON PATH
            );

            SELECT
                @ReadDraftVersion AS draft_version,
                @ReadBasePublicationVersion AS base_publication_version,
                JSON_QUERY(COALESCE(@CommandReceiptsJson, N''[]'')) AS command_receipts_json
            WHERE @ReadDraftId IS NOT NULL;

            SELECT
                item.record_key,
                item.record_type,
                item.base_content_token,
                item.base_access_revision,
                item.proposed_values_json,
                item.intended_permission_expansions_json,
                item.is_new
            FROM dbo.resume_drafts AS draft WITH (UPDLOCK, HOLDLOCK)
            JOIN dbo.resume_draft_items AS item WITH (UPDLOCK, HOLDLOCK)
              ON item.resume_draft_id = draft.resume_draft_id
            WHERE draft.owner_profile_id = @ProfileId
            ORDER BY item.record_type, item.record_key;

            COMMIT TRANSACTION;
            END TRY
            BEGIN CATCH
                IF XACT_STATE() <> 0 ROLLBACK TRANSACTION;
                THROW;
            END CATCH;
        END;';

    EXEC sys.sp_executesql N'CREATE OR ALTER PROCEDURE dbo.usp_CommitResumeDraftCommandForOwner
    @UserKey nvarchar(300),
    @RequestId uniqueidentifier,
    @CommandJson nvarchar(max)
AS
BEGIN
    SET NOCOUNT ON;
    SET XACT_ABORT ON;
    SET TRANSACTION ISOLATION LEVEL SERIALIZABLE;
    DECLARE @OwnTransaction bit = 0;
    IF @@TRANCOUNT = 0
    BEGIN
        BEGIN TRANSACTION;
        SET @OwnTransaction = 1;
    END;
    DECLARE @ProfileId bigint;
    SELECT @ProfileId = profile.profile_id
      FROM dbo.member_profiles AS profile WITH (UPDLOCK, HOLDLOCK)
      JOIN dbo.app_users AS app_user ON app_user.id = profile.user_id
     WHERE app_user.user_key = @UserKey AND app_user.active = 1 AND profile.active = 1;
    IF @ProfileId IS NULL
        THROW 52202, ''RESUME_DRAFT_NOT_FOUND'', 1;
    EXEC dbo.usp_ResumePublicationGuardLegacyMutator
        @ProfileId = @ProfileId, @Mutator = N''draft'', @CommandJson = @CommandJson;
    EXEC dbo.usp_CommitResumeDraftCommandForOwnerCore
        @UserKey = @UserKey, @RequestId = @RequestId, @CommandJson = @CommandJson;
    IF @OwnTransaction = 1 COMMIT TRANSACTION;
END;';

    EXEC sys.sp_executesql N'CREATE OR ALTER PROCEDURE dbo.usp_ResumePublicationBuildManifestsInternal
    @ProfileId bigint,
    @Revision int,
    @CommandJson nvarchar(max),
    @Display nvarchar(max) OUTPUT,
    @VisitorAi nvarchar(max) OUTPUT,
    @Evidence nvarchar(max) OUTPUT
AS
BEGIN
    SET NOCOUNT ON;
    SET XACT_ABORT ON;
    SET @Display = N''{}'';
    SET @VisitorAi = N''{}'';
    SET @Evidence = N''{}'';

    DECLARE @EntryKey uniqueidentifier;
    DECLARE @CanonicalType nvarchar(40);
    DECLARE @ContentVersion int;
    DECLARE @AccessRevision int;
    DECLARE @ResumeDisplay bit;
    DECLARE @VisitorAiFlag bit;
    DECLARE @CanonicalKey uniqueidentifier;
    DECLARE @Fields nvarchar(max);
    DECLARE @Bytes varbinary(max);
    DECLARE @Digest char(64);
    DECLARE @Wording nvarchar(max);

    DECLARE entry_cursor CURSOR LOCAL FAST_FORWARD FOR
        SELECT policy.entry_key, policy.canonical_type, policy.content_version, policy.access_revision,
               policy.resume_display, policy.visitor_ai, policy.canonical_key
          FROM dbo.entry_policy_records AS policy WITH (UPDLOCK, HOLDLOCK)
         WHERE policy.owner_profile_id = @ProfileId
           AND policy.lifecycle = N''active''
           AND (policy.resume_display = 1 OR policy.visitor_ai = 1)
         ORDER BY policy.entry_key;
    OPEN entry_cursor;
    FETCH NEXT FROM entry_cursor INTO @EntryKey, @CanonicalType, @ContentVersion, @AccessRevision,
        @ResumeDisplay, @VisitorAiFlag, @CanonicalKey;
    WHILE @@FETCH_STATUS = 0
    BEGIN
        DECLARE @ExpectedContent int = TRY_CONVERT(int, JSON_VALUE(@CommandJson, CONCAT(N''$.expected_by_entry."'', CONVERT(nvarchar(36), @EntryKey), N''".content_version'')));
        DECLARE @ExpectedAccess int = TRY_CONVERT(int, JSON_VALUE(@CommandJson, CONCAT(N''$.expected_by_entry."'', CONVERT(nvarchar(36), @EntryKey), N''".access_revision'')));
        IF @ExpectedContent IS NOT NULL AND @ExpectedContent <> @ContentVersion
            THROW 54023, ''The publication changed.'', 1;
        IF @ExpectedAccess IS NOT NULL AND @ExpectedAccess <> @AccessRevision
            THROW 54023, ''The publication changed.'', 1;

        SELECT @Fields = (
            SELECT
                @CanonicalType AS canonical_type,
                exp.role_title,
                exp.employer_name,
                chapter.location_text,
                COALESCE(chapter.approved_wording, chapter.summary) AS summary,
                CONVERT(nvarchar(40), chapter.start_date, 23) AS start_date,
                CONVERT(nvarchar(40), chapter.end_date, 23) AS end_date,
                chapter.date_precision,
                exp.employment_type,
                exp.current_role,
                chapter.title,
                edu.institution_name,
                edu.degree_name,
                edu.field_of_study,
                edu.education_status,
                edu.grade_text,
                cred.credential_name,
                cred.issuer_name,
                cred.credential_identifier,
                CONVERT(nvarchar(40), cred.issue_date, 23) AS issue_date,
                CONVERT(nvarchar(40), cred.expiration_date, 23) AS expiration_date,
                skill.skill_name AS name,
                COALESCE(chapter.summary, skill.skill_summary) AS skill_summary,
                COALESCE(chapter.approved_wording, ach.approved_wording, ach.original_member_wording) AS wording,
                ach.metric_value,
                ach.metric_label,
                CONVERT(bit, NULL) AS accomplishment_to_achievement,
                parent.canonical_type AS parent_canonical_type
            FROM dbo.entry_policy_records AS policy
            LEFT JOIN dbo.career_chapters AS chapter
              ON chapter.owner_profile_id = policy.owner_profile_id
             AND chapter.chapter_key = policy.canonical_key
            LEFT JOIN dbo.career_experiences AS exp
              ON exp.chapter_id = chapter.chapter_id AND exp.owner_profile_id = chapter.owner_profile_id
            LEFT JOIN dbo.career_education AS edu
              ON edu.chapter_id = chapter.chapter_id AND edu.owner_profile_id = chapter.owner_profile_id
            LEFT JOIN dbo.career_credentials AS cred
              ON cred.chapter_id = chapter.chapter_id AND cred.owner_profile_id = chapter.owner_profile_id
            LEFT JOIN dbo.career_skills AS skill
              ON skill.owner_profile_id = policy.owner_profile_id
             AND skill.skill_key = policy.canonical_key
            LEFT JOIN dbo.career_achievements AS ach
              ON ach.owner_profile_id = policy.owner_profile_id
             AND ach.achievement_key = policy.canonical_key
            LEFT JOIN dbo.career_projects AS proj
              ON proj.chapter_id = chapter.chapter_id AND proj.owner_profile_id = chapter.owner_profile_id
            LEFT JOIN dbo.entry_policy_records AS parent
              ON parent.owner_profile_id = policy.owner_profile_id
             AND parent.entry_key = policy.parent_entry_key
            WHERE policy.owner_profile_id = @ProfileId
              AND policy.entry_key = @EntryKey
            FOR JSON PATH, WITHOUT_ARRAY_WRAPPER
        );

        IF @Fields IS NULL OR ISJSON(@Fields) <> 1
            THROW 54015, ''Canonical source is unavailable.'', 1;
        IF @CanonicalType = N''education'' AND JSON_VALUE(@Fields, ''$.institution_name'') IS NULL
            THROW 54015, ''Canonical source is unavailable.'', 1;
        IF @CanonicalType = N''credential'' AND JSON_VALUE(@Fields, ''$.credential_name'') IS NULL
            THROW 54015, ''Canonical source is unavailable.'', 1;
        IF @CanonicalType = N''skill'' AND JSON_VALUE(@Fields, ''$.name'') IS NULL
            THROW 54015, ''Canonical source is unavailable.'', 1;
        IF @CanonicalType = N''achievement'' AND JSON_VALUE(@Fields, ''$.wording'') IS NULL
            THROW 54015, ''Canonical source is unavailable.'', 1;

        EXEC dbo.usp_ResumePublicationEncodeSourceInternal
            @FieldsJson = @Fields, @Bytes = @Bytes OUTPUT, @Digest = @Digest OUTPUT;

        DECLARE @EvidenceKey nvarchar(120) = CONCAT(N''evidence:'', CONVERT(nvarchar(36), @EntryKey), N'':'', CONVERT(nvarchar(20), @Revision));
        INSERT dbo.resume_publication_evidence
            (owner_profile_id, entry_key, evidence_version_key, codec, canonical_token,
             policy_content_version, access_revision, content_bytes, content_sha256,
             display_eligible, visitor_ai_eligible)
        VALUES
            (@ProfileId, @EntryKey, @EvidenceKey, N''resume-canonical-source.v1'',
             CONVERT(nvarchar(100), @ContentVersion), @ContentVersion, @AccessRevision,
             @Bytes, @Digest, @ResumeDisplay, @VisitorAiFlag);
        IF CONVERT(nvarchar(20), SESSION_CONTEXT(N''resume_publication_proof_fail_after_evidence'')) = N''1''
            THROW 54999, ''PROOF_INJECTED_FAILURE'', 1;

        SET @Wording = COALESCE(JSON_QUERY(@Fields, N''$''), N''{}'');
        IF @ResumeDisplay = 1
            SET @Display = JSON_MODIFY(@Display, CONCAT(N''$."'', CONVERT(nvarchar(36), @EntryKey), N''"''),
                JSON_QUERY(CONCAT(N''{"wording":'', @Wording, N'',"evidence_sha256":"'', @Digest, N''","canonical_token":"'', CONVERT(nvarchar(100), @ContentVersion), N''"}'')));
        IF @VisitorAiFlag = 1
            SET @VisitorAi = JSON_MODIFY(@VisitorAi, CONCAT(N''$."'', CONVERT(nvarchar(36), @EntryKey), N''"''),
                JSON_QUERY(CONCAT(N''{"wording":'', @Wording, N'',"evidence_sha256":"'', @Digest, N''","canonical_token":"'', CONVERT(nvarchar(100), @ContentVersion), N''"}'')));
        SET @Evidence = JSON_MODIFY(@Evidence, CONCAT(N''$."'', CONVERT(nvarchar(36), @EntryKey), N''"''),
            JSON_QUERY(CONCAT(N''{"content_sha256":"'', @Digest, N''","codec":"resume-canonical-source.v1"}'')));

        FETCH NEXT FROM entry_cursor INTO @EntryKey, @CanonicalType, @ContentVersion, @AccessRevision,
            @ResumeDisplay, @VisitorAiFlag, @CanonicalKey;
    END;
    CLOSE entry_cursor;
    DEALLOCATE entry_cursor;
END;';

    EXEC sys.sp_executesql N'CREATE OR ALTER PROCEDURE dbo.usp_ListResumePublicationPolicyForOwner
    @UserKey nvarchar(300)
AS
BEGIN
    SET NOCOUNT ON;
    DECLARE @ProfileId bigint;
    SELECT @ProfileId = profile.profile_id
      FROM dbo.member_profiles AS profile
      JOIN dbo.app_users AS app_user ON app_user.id = profile.user_id
     WHERE app_user.user_key = @UserKey AND app_user.active = 1 AND profile.active = 1;
    IF @ProfileId IS NULL
        THROW 54021, ''Owner is unavailable.'', 1;

    SELECT policy.entry_key, policy.canonical_type, policy.canonical_key, policy.category,
           policy.parent_entry_key, policy.content_version, policy.access_revision,
           policy.resume_display, policy.visitor_ai, policy.private_assistance_excluded,
           policy.lifecycle, policy.recover_until_utc,
           (
               SELECT exp.role_title, exp.employer_name, chapter.location_text,
                      COALESCE(chapter.approved_wording, chapter.summary) AS summary,
                      CONVERT(nvarchar(40), chapter.start_date, 23) AS start_date,
                      CONVERT(nvarchar(40), chapter.end_date, 23) AS end_date,
                      chapter.date_precision, exp.employment_type, exp.current_role,
                      chapter.title, edu.institution_name, edu.degree_name,
                      edu.field_of_study, edu.education_status, edu.grade_text,
                      cred.credential_name, cred.issuer_name, cred.credential_identifier,
                      CONVERT(nvarchar(40), cred.issue_date, 23) AS issue_date,
                      CONVERT(nvarchar(40), cred.expiration_date, 23) AS expiration_date,
                      skill.skill_name AS name, skill.skill_summary,
                      COALESCE(chapter.approved_wording, ach.approved_wording, ach.original_member_wording) AS wording,
                      ach.metric_value, ach.metric_label
                 FOR JSON PATH, WITHOUT_ARRAY_WRAPPER
           ) AS values_json
      FROM dbo.entry_policy_records AS policy
      LEFT JOIN dbo.career_chapters AS chapter
        ON chapter.owner_profile_id = policy.owner_profile_id
       AND chapter.chapter_key = policy.canonical_key
      LEFT JOIN dbo.career_experiences AS exp
        ON exp.owner_profile_id = chapter.owner_profile_id AND exp.chapter_id = chapter.chapter_id
      LEFT JOIN dbo.career_education AS edu
        ON edu.owner_profile_id = chapter.owner_profile_id AND edu.chapter_id = chapter.chapter_id
      LEFT JOIN dbo.career_credentials AS cred
        ON cred.owner_profile_id = chapter.owner_profile_id AND cred.chapter_id = chapter.chapter_id
      LEFT JOIN dbo.career_skills AS skill
        ON skill.owner_profile_id = policy.owner_profile_id AND skill.skill_key = policy.canonical_key
      LEFT JOIN dbo.career_achievements AS ach
        ON ach.owner_profile_id = policy.owner_profile_id AND ach.achievement_key = policy.canonical_key
     WHERE policy.owner_profile_id = @ProfileId
       AND policy.lifecycle <> N''permanently_deleted''
     ORDER BY policy.category, policy.entry_key;
END;';

    EXEC sys.sp_executesql N'CREATE OR ALTER PROCEDURE dbo.usp_ResumePublicationApplyCanonicalInternal
    @ProfileId bigint,
    @CommandJson nvarchar(max)
AS
BEGIN
    SET NOCOUNT ON;
    SET XACT_ABORT ON;
    DECLARE @Type nvarchar(40) = JSON_VALUE(@CommandJson, ''$.type'');
    DECLARE @EntryKey uniqueidentifier = TRY_CONVERT(uniqueidentifier, JSON_VALUE(@CommandJson, ''$.entry_key''));
    DECLARE @Now datetime2(7) = SYSUTCDATETIME();

    IF @Type IN (N''edit'', N''correct'')
    BEGIN
        IF @EntryKey IS NULL
            THROW 54026, ''Entry is unavailable.'', 1;
        DECLARE @ExpectedContent int = TRY_CONVERT(int, JSON_VALUE(@CommandJson, ''$.expected_content_version''));
        DECLARE @ExpectedAccess int = TRY_CONVERT(int, JSON_VALUE(@CommandJson, ''$.expected_access_revision''));
        IF @ExpectedContent IS NULL OR @ExpectedAccess IS NULL
            THROW 54027, ''Expected content and access versions are required.'', 1;

        DECLARE @Lifecycle nvarchar(30);
        DECLARE @ContentVersion int;
        DECLARE @AccessRevision int;
        DECLARE @CanonicalType nvarchar(40);
        DECLARE @CanonicalKey uniqueidentifier;
        SELECT @Lifecycle = policy.lifecycle,
               @ContentVersion = policy.content_version,
               @AccessRevision = policy.access_revision,
               @CanonicalType = policy.canonical_type,
               @CanonicalKey = policy.canonical_key
          FROM dbo.entry_policy_records AS policy WITH (UPDLOCK, HOLDLOCK)
         WHERE policy.owner_profile_id = @ProfileId
           AND policy.entry_key = @EntryKey;
        IF @CanonicalKey IS NULL
            THROW 54026, ''Entry is unavailable.'', 1;
        IF @Lifecycle <> N''active''
            THROW 54028, ''Entry is not active.'', 1;
        IF @ContentVersion <> @ExpectedContent OR @AccessRevision <> @ExpectedAccess
            THROW 54023, ''The publication changed.'', 1;

        IF @CanonicalType IN (N''role'', N''education'', N''credential'', N''project'')
        BEGIN
            IF NOT EXISTS (
                SELECT 1
                  FROM dbo.career_chapters AS chapter WITH (UPDLOCK, HOLDLOCK)
                 WHERE chapter.owner_profile_id = @ProfileId
                   AND chapter.chapter_key = @CanonicalKey)
                THROW 54026, ''Canonical source is unavailable.'', 1;
        END
        ELSE IF @CanonicalType = N''skill''
        BEGIN
            IF NOT EXISTS (
                SELECT 1
                  FROM dbo.career_skills AS skill WITH (UPDLOCK, HOLDLOCK)
                 WHERE skill.owner_profile_id = @ProfileId
                   AND skill.skill_key = @CanonicalKey)
                THROW 54026, ''Canonical source is unavailable.'', 1;
        END
        ELSE IF @CanonicalType = N''achievement''
        BEGIN
            IF NOT EXISTS (
                SELECT 1
                  FROM dbo.career_achievements AS achievement WITH (UPDLOCK, HOLDLOCK)
                 WHERE achievement.owner_profile_id = @ProfileId
                   AND achievement.achievement_key = @CanonicalKey)
                THROW 54026, ''Canonical source is unavailable.'', 1;
        END
        ELSE
            THROW 54026, ''Canonical source is unavailable.'', 1;

        -- My Data shows summary and wording as aliases for the same approved
        -- chapter text. A form can change either field while submitting both.
        -- Compare exact UTF-16 bytes with the displayed value so a case-only
        -- edit counts and an unchanged alias cannot undo the edited one.
        -- Summary wins only when both aliases changed.
        UPDATE chapter
           SET summary = COALESCE(next_wording.wording, chapter.summary),
               approved_wording = COALESCE(next_wording.wording, chapter.approved_wording),
               title = COALESCE(
                    JSON_VALUE(@CommandJson, ''$.values.role_title''),
                    JSON_VALUE(@CommandJson, ''$.values.title''),
                    chapter.title),
               updated_at_utc = @Now
          FROM dbo.career_chapters AS chapter WITH (UPDLOCK, HOLDLOCK)
          JOIN dbo.entry_policy_records AS policy WITH (UPDLOCK, HOLDLOCK)
            ON policy.owner_profile_id = chapter.owner_profile_id
           AND policy.canonical_key = chapter.chapter_key
          CROSS APPLY (SELECT
              COALESCE(JSON_VALUE(@CommandJson, ''$.values.summary''),
                       JSON_VALUE(@CommandJson, ''$.fields.summary'')) AS submitted_summary,
              COALESCE(JSON_VALUE(@CommandJson, ''$.values.wording''),
                       JSON_VALUE(@CommandJson, ''$.fields.wording'')) AS submitted_wording,
              COALESCE(chapter.approved_wording, chapter.summary) AS displayed_wording
          ) AS submitted
          CROSS APPLY (SELECT CASE
              WHEN submitted.submitted_summary IS NOT NULL
                   AND (DATALENGTH(submitted.submitted_summary) <> DATALENGTH(submitted.displayed_wording)
                        OR CONVERT(varbinary(max), submitted.submitted_summary)
                           <> CONVERT(varbinary(max), submitted.displayed_wording))
                  THEN submitted.submitted_summary
              WHEN submitted.submitted_wording IS NOT NULL
                   AND (DATALENGTH(submitted.submitted_wording) <> DATALENGTH(submitted.displayed_wording)
                        OR CONVERT(varbinary(max), submitted.submitted_wording)
                           <> CONVERT(varbinary(max), submitted.displayed_wording))
                  THEN submitted.submitted_wording
              ELSE COALESCE(submitted.submitted_summary, submitted.submitted_wording)
          END AS wording) AS next_wording
         WHERE policy.owner_profile_id = @ProfileId
           AND policy.entry_key = @EntryKey;
        IF @CanonicalType IN (N''role'', N''education'', N''credential'', N''project'')
           AND @@ROWCOUNT <> 1
            THROW 54029, ''Canonical source did not change.'', 1;

        UPDATE dbo.career_experiences WITH (UPDLOCK, HOLDLOCK)
           SET role_title = COALESCE(JSON_VALUE(@CommandJson, ''$.values.role_title''), role_title),
               employer_name = COALESCE(JSON_VALUE(@CommandJson, ''$.values.employer_name''), employer_name),
               employment_type = COALESCE(JSON_VALUE(@CommandJson, ''$.values.employment_type''), employment_type),
               current_role = COALESCE(TRY_CONVERT(bit, JSON_VALUE(@CommandJson, ''$.values.current_role'')), current_role)
         WHERE owner_profile_id = @ProfileId
           AND chapter_id IN (
                SELECT chapter.chapter_id
                  FROM dbo.career_chapters AS chapter
                  JOIN dbo.entry_policy_records AS policy
                    ON policy.canonical_key = chapter.chapter_key
                   AND policy.owner_profile_id = chapter.owner_profile_id
                 WHERE policy.owner_profile_id = @ProfileId
                   AND policy.entry_key = @EntryKey);

        UPDATE dbo.career_education WITH (UPDLOCK, HOLDLOCK)
           SET institution_name = COALESCE(JSON_VALUE(@CommandJson, ''$.values.institution_name''), institution_name),
               degree_name = COALESCE(JSON_VALUE(@CommandJson, ''$.values.degree_name''), degree_name),
               field_of_study = COALESCE(JSON_VALUE(@CommandJson, ''$.values.field_of_study''), field_of_study),
               education_status = COALESCE(JSON_VALUE(@CommandJson, ''$.values.education_status''), education_status),
               grade_text = COALESCE(JSON_VALUE(@CommandJson, ''$.values.grade_text''), grade_text)
         WHERE owner_profile_id = @ProfileId
           AND chapter_id IN (
                SELECT chapter.chapter_id
                  FROM dbo.career_chapters AS chapter
                  JOIN dbo.entry_policy_records AS policy
                    ON policy.canonical_key = chapter.chapter_key
                   AND policy.owner_profile_id = chapter.owner_profile_id
                 WHERE policy.owner_profile_id = @ProfileId
                   AND policy.entry_key = @EntryKey);

        UPDATE dbo.career_credentials WITH (UPDLOCK, HOLDLOCK)
           SET credential_name = COALESCE(JSON_VALUE(@CommandJson, ''$.values.credential_name''), credential_name),
               issuer_name = COALESCE(JSON_VALUE(@CommandJson, ''$.values.issuer_name''), issuer_name),
               credential_identifier = COALESCE(JSON_VALUE(@CommandJson, ''$.values.credential_identifier''), credential_identifier),
               issue_date = COALESCE(TRY_CONVERT(date, JSON_VALUE(@CommandJson, ''$.values.issue_date'')), issue_date),
               expiration_date = COALESCE(TRY_CONVERT(date, JSON_VALUE(@CommandJson, ''$.values.expiration_date'')), expiration_date)
         WHERE owner_profile_id = @ProfileId
           AND chapter_id IN (
                SELECT chapter.chapter_id
                  FROM dbo.career_chapters AS chapter
                  JOIN dbo.entry_policy_records AS policy
                    ON policy.canonical_key = chapter.chapter_key
                   AND policy.owner_profile_id = chapter.owner_profile_id
                 WHERE policy.owner_profile_id = @ProfileId
                   AND policy.entry_key = @EntryKey);

        UPDATE dbo.career_projects WITH (UPDLOCK, HOLDLOCK)
           SET project_name = COALESCE(JSON_VALUE(@CommandJson, ''$.values.title''), JSON_VALUE(@CommandJson, ''$.values.project_name''), project_name),
               project_role = COALESCE(JSON_VALUE(@CommandJson, ''$.values.project_role''), project_role)
         WHERE owner_profile_id = @ProfileId
           AND chapter_id IN (
                SELECT chapter.chapter_id
                  FROM dbo.career_chapters AS chapter
                  JOIN dbo.entry_policy_records AS policy
                    ON policy.canonical_key = chapter.chapter_key
                   AND policy.owner_profile_id = chapter.owner_profile_id
                 WHERE policy.owner_profile_id = @ProfileId
                   AND policy.entry_key = @EntryKey);

        UPDATE dbo.career_skills WITH (UPDLOCK, HOLDLOCK)
           SET skill_name = COALESCE(JSON_VALUE(@CommandJson, ''$.values.name''), skill_name),
               skill_summary = COALESCE(
                    JSON_VALUE(@CommandJson, ''$.values.skill_summary''),
                    JSON_VALUE(@CommandJson, ''$.values.summary''),
                    skill_summary),
               updated_at_utc = @Now
         WHERE owner_profile_id = @ProfileId
           AND skill_key IN (
                SELECT policy.canonical_key
                  FROM dbo.entry_policy_records AS policy WITH (UPDLOCK, HOLDLOCK)
                 WHERE policy.owner_profile_id = @ProfileId
                   AND policy.entry_key = @EntryKey);
        IF @CanonicalType = N''skill'' AND @@ROWCOUNT <> 1
            THROW 54029, ''Canonical source did not change.'', 1;

        UPDATE dbo.career_achievements WITH (UPDLOCK, HOLDLOCK)
           SET approved_wording = COALESCE(
                    JSON_VALUE(@CommandJson, ''$.values.wording''),
                    JSON_VALUE(@CommandJson, ''$.fields.wording''),
                    approved_wording),
               metric_value = COALESCE(JSON_VALUE(@CommandJson, ''$.values.metric_value''), metric_value),
               metric_label = COALESCE(JSON_VALUE(@CommandJson, ''$.values.metric_label''), metric_label),
               updated_at_utc = @Now
         WHERE owner_profile_id = @ProfileId
           AND achievement_key IN (
                SELECT policy.canonical_key
                  FROM dbo.entry_policy_records AS policy WITH (UPDLOCK, HOLDLOCK)
                 WHERE policy.owner_profile_id = @ProfileId
                   AND policy.entry_key = @EntryKey);
        IF @CanonicalType = N''achievement'' AND @@ROWCOUNT <> 1
            THROW 54029, ''Canonical source did not change.'', 1;

        UPDATE dbo.entry_policy_records WITH (UPDLOCK, HOLDLOCK)
           SET content_version = content_version + 1,
               updated_at_utc = @Now
         WHERE owner_profile_id = @ProfileId
           AND entry_key = @EntryKey
           AND lifecycle = N''active''
           AND content_version = @ExpectedContent
           AND access_revision = @ExpectedAccess;
        IF @@ROWCOUNT <> 1
            THROW 54023, ''The publication changed.'', 1;
    END;

    IF @Type = N''change_permissions''
    BEGIN
        DECLARE @PermissionTargets TABLE (
            entry_key uniqueidentifier NULL,
            expected_access_revision int NULL,
            permissions nvarchar(max) NULL
        );
        DECLARE @TargetsJson nvarchar(max) = JSON_QUERY(@CommandJson, ''$.targets'');
        IF EXISTS (SELECT 1 FROM OPENJSON(@CommandJson) WHERE [key] = N''targets'')
        BEGIN
            IF @TargetsJson IS NULL OR LEFT(LTRIM(@TargetsJson), 1) <> N''[''
                THROW 54061, ''Invalid permission targets.'', 1;
            INSERT @PermissionTargets (entry_key, expected_access_revision, permissions)
            SELECT TRY_CONVERT(uniqueidentifier, JSON_VALUE(value, ''$.entry_key'')),
                   TRY_CONVERT(int, JSON_VALUE(value, ''$.expected_access_revision'')),
                   JSON_QUERY(value, ''$.permissions'')
              FROM OPENJSON(@TargetsJson);
        END
        ELSE
            INSERT @PermissionTargets (entry_key, expected_access_revision, permissions)
            VALUES (@EntryKey,
                    TRY_CONVERT(int, JSON_VALUE(@CommandJson, ''$.expected_access_revision'')),
                    JSON_QUERY(@CommandJson, ''$.permissions''));

        DECLARE @TargetCount int = (SELECT COUNT(*) FROM @PermissionTargets);
        IF @TargetCount = 0 OR EXISTS (
            SELECT 1 FROM @PermissionTargets
             WHERE entry_key IS NULL OR expected_access_revision IS NULL
                OR permissions IS NULL OR LEFT(LTRIM(permissions), 1) <> N''{''
            ) OR EXISTS (
            SELECT entry_key FROM @PermissionTargets GROUP BY entry_key HAVING COUNT(*) > 1
            ) OR EXISTS (
            SELECT 1 FROM @PermissionTargets AS target
             WHERE NOT EXISTS (SELECT 1 FROM OPENJSON(target.permissions))
                OR EXISTS (SELECT 1 FROM OPENJSON(target.permissions) AS field
                            WHERE field.[key] NOT IN (N''resume_display'', N''visitor_ai'', N''private_assistance_excluded'')
                               OR field.[type] <> 3)
            ) OR (@TargetsJson IS NOT NULL AND @EntryKey IS NOT NULL AND NOT EXISTS (
                SELECT 1 FROM @PermissionTargets WHERE entry_key = @EntryKey))
            THROW 54061, ''Invalid permission targets.'', 1;

        -- The owner transaction holds the publication lock. Check every target
        -- before changing any policy row; one conflict rolls back the batch.
        IF EXISTS (
            SELECT 1 FROM @PermissionTargets AS target
            LEFT JOIN dbo.entry_policy_records AS policy WITH (UPDLOCK, HOLDLOCK)
              ON policy.owner_profile_id = @ProfileId AND policy.entry_key = target.entry_key
            WHERE policy.entry_key IS NULL OR policy.lifecycle <> N''active''
               OR policy.access_revision <> target.expected_access_revision)
            THROW 54014, ''ENTRY_POLICY_CHANGED'', 1;

        UPDATE policy
           SET resume_display = COALESCE(TRY_CONVERT(bit, JSON_VALUE(target.permissions, ''$.resume_display'')), policy.resume_display),
               visitor_ai = COALESCE(TRY_CONVERT(bit, JSON_VALUE(target.permissions, ''$.visitor_ai'')), policy.visitor_ai),
               private_assistance_excluded = COALESCE(TRY_CONVERT(bit, JSON_VALUE(target.permissions, ''$.private_assistance_excluded'')), policy.private_assistance_excluded),
               access_revision = policy.access_revision + 1,
               updated_at_utc = @Now
          FROM dbo.entry_policy_records AS policy WITH (UPDLOCK, HOLDLOCK)
          JOIN @PermissionTargets AS target ON target.entry_key = policy.entry_key
         WHERE policy.owner_profile_id = @ProfileId
           AND policy.lifecycle = N''active''
           AND policy.access_revision = target.expected_access_revision;
        IF @@ROWCOUNT <> @TargetCount
            THROW 54014, ''ENTRY_POLICY_CHANGED'', 1;
    END;

    IF @Type = N''delete''
    BEGIN
        UPDATE dbo.entry_policy_records WITH (UPDLOCK, HOLDLOCK)
           SET lifecycle = N''deleted'',
               resume_display = 0,
               visitor_ai = 0,
               deleted_at_utc = @Now,
               recover_until_utc = DATEADD(day, 30, @Now),
               access_revision = access_revision + 1,
               updated_at_utc = @Now
         WHERE owner_profile_id = @ProfileId
           AND (entry_key = @EntryKey OR parent_entry_key = @EntryKey)
           AND lifecycle = N''active'';
    END;

    IF @Type = N''restore''
    BEGIN
        UPDATE dbo.entry_policy_records WITH (UPDLOCK, HOLDLOCK)
           SET lifecycle = N''active'',
               resume_display = 0,
               visitor_ai = 0,
               deleted_at_utc = NULL,
               recover_until_utc = NULL,
               access_revision = access_revision + 1,
               updated_at_utc = @Now
         WHERE owner_profile_id = @ProfileId
           AND entry_key = @EntryKey
           AND lifecycle = N''deleted'';
    END;
END;';

    EXEC sys.sp_executesql N'CREATE OR ALTER PROCEDURE dbo.usp_MemberVisitorAiSnapshotInternal
    @UserKey nvarchar(300) = NULL, @ProfileSlug nvarchar(100) = NULL,
    @OwnerPreview bit
AS
BEGIN
    SET NOCOUNT ON;
    SET XACT_ABORT ON;
    -- This reader must own its transaction; no caller can retain locks through AI work.
    IF @@TRANCOUNT <> 0 THROW 54201, ''AI source authority is unavailable.'', 1;
    IF @OwnerPreview IS NULL OR (@OwnerPreview = 1 AND (@UserKey IS NULL OR @ProfileSlug IS NOT NULL))
       OR (@OwnerPreview = 0 AND (@ProfileSlug IS NULL OR @UserKey IS NOT NULL))
        THROW 54201, ''AI source authority is unavailable.'', 1;
    BEGIN TRY
    BEGIN TRANSACTION;
    DECLARE @ProfileId bigint, @Subject nvarchar(300), @ProfileVersion varchar(16);
    -- Resolve first, then re-prove identity under locks after the sharing lock.
    IF @OwnerPreview = 1
        SELECT @ProfileId=p.profile_id FROM dbo.member_profiles p JOIN dbo.app_users u ON u.id=p.user_id
        WHERE u.user_key=@UserKey AND u.active=1 AND p.active=1;
    ELSE
        SELECT @ProfileId=owner_profile_id FROM dbo.resume_sharing_state WHERE public_slug=@ProfileSlug;
    IF @ProfileId IS NULL THROW 54201, ''AI source authority is unavailable.'', 1;
    DECLARE @Sharing bit=0, @Epoch int=0, @Revision int=0, @Current int=NULL, @Slug nvarchar(100);
    -- Shared E lock order: sharing, sorted policy, draft, publication, media/catalog.
    SELECT @Sharing=sharing_enabled,@Epoch=sharing_epoch,@Revision=publication_revision,
           @Current=current_revision,@Slug=public_slug
      FROM dbo.resume_sharing_state WITH (UPDLOCK,HOLDLOCK) WHERE owner_profile_id=@ProfileId;
    IF @OwnerPreview=0 AND (@Sharing<>1 OR @Current IS NULL OR @Slug<>@ProfileSlug)
        THROW 54201, ''AI source authority is unavailable.'', 1;
    SELECT @Subject=CONVERT(nvarchar(300),u.user_key),@ProfileVersion=CONVERT(varchar(16),p.row_version,2)
      FROM dbo.member_profiles p WITH (HOLDLOCK) JOIN dbo.app_users u WITH (HOLDLOCK) ON u.id=p.user_id
      WHERE p.profile_id=@ProfileId AND u.active=1 AND p.active=1;
    IF @Subject IS NULL OR (@OwnerPreview=1 AND @Subject<>@UserKey)
        THROW 54201, ''AI source authority is unavailable.'', 1;
    DECLARE @LockEntry uniqueidentifier;
    DECLARE policy_locks CURSOR LOCAL FAST_FORWARD FOR
        SELECT entry_key FROM dbo.entry_policy_records WITH (UPDLOCK,HOLDLOCK)
        WHERE owner_profile_id=@ProfileId ORDER BY entry_key;
    OPEN policy_locks; FETCH NEXT FROM policy_locks INTO @LockEntry;
    WHILE @@FETCH_STATUS=0 FETCH NEXT FROM policy_locks INTO @LockEntry;
    CLOSE policy_locks; DEALLOCATE policy_locks;
    DECLARE @DraftId bigint, @Draft int=0, @DraftJson nvarchar(max);
    SELECT @DraftId=resume_draft_id,@Draft=draft_version FROM dbo.resume_drafts WITH (UPDLOCK,HOLDLOCK)
        WHERE owner_profile_id=@ProfileId;
    SELECT @DraftJson=(SELECT record_key,record_type,base_content_token,base_access_revision,
        proposed_values_json,intended_permission_expansions_json,is_new
        FROM dbo.resume_draft_items WITH (HOLDLOCK) WHERE resume_draft_id=@DraftId
        ORDER BY record_key FOR JSON PATH,INCLUDE_NULL_VALUES);
    DECLARE @Visitor nvarchar(max), @Media nvarchar(max), @Reviewed char(64);
    SELECT @Visitor=visitor_ai_json,@Media=media_json,@Reviewed=reviewed_digest
        FROM dbo.resume_publication_revisions WITH (UPDLOCK,HOLDLOCK)
        WHERE owner_profile_id=@ProfileId AND publication_revision=@Current;
    IF @OwnerPreview=0 AND (@Visitor IS NULL OR ISJSON(@Visitor)<>1 OR ISJSON(@Media)<>1)
        THROW 54201, ''AI source authority is unavailable.'', 1;
    SET @Media=COALESCE(@Media,N''{}'');
    -- Missing/duplicate/foreign/stale manifest members deny the complete guest snapshot.
    IF @OwnerPreview=0 AND (EXISTS(SELECT [key] FROM OPENJSON(@Visitor) GROUP BY [key] HAVING COUNT(*)<>1)
        OR EXISTS(SELECT 1 FROM OPENJSON(@Visitor) j LEFT JOIN dbo.entry_policy_records p
            ON p.owner_profile_id=@ProfileId AND p.entry_key=TRY_CONVERT(uniqueidentifier,j.[key])
            WHERE LEN(j.[key])<>36 OR p.entry_key IS NULL OR p.lifecycle<>N''active'' OR p.visitor_ai<>1))
        THROW 54201, ''AI source authority is unavailable.'', 1;
    DECLARE @Entries table(entry_key uniqueidentifier PRIMARY KEY,payload nvarchar(max));
    DECLARE @EntryKey uniqueidentifier,@CanonicalType nvarchar(40),@ContentVersion int,@Access int,
        @Display bit,@Ai bit,@CanonicalKey uniqueidentifier,@Parent uniqueidentifier;
    DECLARE entry_cursor CURSOR LOCAL FAST_FORWARD FOR
        SELECT p.entry_key,p.canonical_type,p.content_version,p.access_revision,p.resume_display,p.visitor_ai,p.canonical_key,p.parent_entry_key
        FROM dbo.entry_policy_records p WHERE p.owner_profile_id=@ProfileId AND p.lifecycle=N''active''
        AND (@OwnerPreview=1 OR (p.visitor_ai=1 AND EXISTS(SELECT 1 FROM OPENJSON(@Visitor) j WHERE TRY_CONVERT(uniqueidentifier,j.[key])=p.entry_key)))
        ORDER BY p.entry_key;
    OPEN entry_cursor;
    FETCH NEXT FROM entry_cursor INTO @EntryKey,@CanonicalType,@ContentVersion,@Access,@Display,@Ai,@CanonicalKey,@Parent;
    WHILE @@FETCH_STATUS=0
    BEGIN
        IF @CanonicalType NOT IN (N''role'',N''education'',N''credential'',N''skill'',N''achievement'',N''project'',N''knowledge'')
            THROW 54201, ''AI source authority is unavailable.'', 1;
        DECLARE @ParentVersion nvarchar(300)=N''none'';
        IF @Parent IS NOT NULL
        BEGIN
            SET @ParentVersion=NULL;
            SELECT @ParentVersion=CONCAT(CONVERT(nvarchar(36),entry_key),N'':'',content_version,N'':'',access_revision,N'':'',lifecycle)
            FROM dbo.entry_policy_records WHERE owner_profile_id=@ProfileId AND entry_key=@Parent AND lifecycle=N''active'';
            IF @ParentVersion IS NULL THROW 54201, ''AI source authority is unavailable.'', 1;
        END;
        DECLARE @CanonicalRevision varchar(16)=NULL;
        SELECT @CanonicalRevision=CASE
            WHEN @CanonicalType=N''skill'' THEN CONVERT(varchar(16),s.row_version,2)
            WHEN @CanonicalType=N''achievement'' THEN CONVERT(varchar(16),a.row_version,2)
            WHEN @CanonicalType=N''role'' AND EXISTS(SELECT 1 FROM dbo.career_experiences x WITH (HOLDLOCK) WHERE x.chapter_id=c.chapter_id AND x.owner_profile_id=@ProfileId) THEN CONVERT(varchar(16),c.row_version,2)
            WHEN @CanonicalType=N''education'' AND EXISTS(SELECT 1 FROM dbo.career_education x WITH (HOLDLOCK) WHERE x.chapter_id=c.chapter_id AND x.owner_profile_id=@ProfileId) THEN CONVERT(varchar(16),c.row_version,2)
            WHEN @CanonicalType=N''credential'' AND EXISTS(SELECT 1 FROM dbo.career_credentials x WITH (HOLDLOCK) WHERE x.chapter_id=c.chapter_id AND x.owner_profile_id=@ProfileId) THEN CONVERT(varchar(16),c.row_version,2)
            WHEN @CanonicalType=N''project'' AND EXISTS(SELECT 1 FROM dbo.career_projects x WITH (HOLDLOCK) WHERE x.chapter_id=c.chapter_id AND x.owner_profile_id=@ProfileId) THEN CONVERT(varchar(16),c.row_version,2)
            WHEN @CanonicalType=N''knowledge'' THEN CONVERT(varchar(16),c.row_version,2) END
        FROM dbo.entry_policy_records p
        LEFT JOIN dbo.career_chapters c WITH (HOLDLOCK) ON c.owner_profile_id=p.owner_profile_id AND c.chapter_key=p.canonical_key AND c.deleted_at_utc IS NULL
        LEFT JOIN dbo.career_achievements a WITH (HOLDLOCK) ON a.owner_profile_id=p.owner_profile_id AND a.achievement_key=p.canonical_key AND a.deleted_at_utc IS NULL
        LEFT JOIN dbo.career_skills s WITH (HOLDLOCK) ON s.owner_profile_id=p.owner_profile_id AND s.skill_key=p.canonical_key AND s.deleted_at_utc IS NULL
        WHERE p.owner_profile_id=@ProfileId AND p.entry_key=@EntryKey;
        IF @CanonicalRevision IS NULL THROW 54201, ''AI source authority is unavailable.'', 1;
        DECLARE @Fields nvarchar(max),@Bytes varbinary(max),@Digest char(64);
        SELECT @Fields = (
            SELECT
                @CanonicalType AS canonical_type,
                exp.role_title,
                exp.employer_name,
                chapter.location_text,
                COALESCE(chapter.approved_wording, chapter.summary) AS summary,
                CONVERT(nvarchar(40), chapter.start_date, 23) AS start_date,
                CONVERT(nvarchar(40), chapter.end_date, 23) AS end_date,
                chapter.date_precision,
                exp.employment_type,
                exp.current_role,
                chapter.title,
                edu.institution_name,
                edu.degree_name,
                edu.field_of_study,
                edu.education_status,
                edu.grade_text,
                cred.credential_name,
                cred.issuer_name,
                cred.credential_identifier,
                CONVERT(nvarchar(40), cred.issue_date, 23) AS issue_date,
                CONVERT(nvarchar(40), cred.expiration_date, 23) AS expiration_date,
                skill.skill_name AS name,
                COALESCE(chapter.summary, skill.skill_summary) AS skill_summary,
                COALESCE(chapter.approved_wording, ach.approved_wording, ach.original_member_wording) AS wording,
                ach.metric_value,
                ach.metric_label,
                CONVERT(bit, NULL) AS accomplishment_to_achievement,
                parent.canonical_type AS parent_canonical_type
            FROM dbo.entry_policy_records AS policy
            LEFT JOIN dbo.career_chapters AS chapter WITH (HOLDLOCK)
              ON chapter.owner_profile_id = policy.owner_profile_id
             AND chapter.chapter_key = policy.canonical_key
            LEFT JOIN dbo.career_experiences AS exp WITH (HOLDLOCK)
              ON exp.chapter_id = chapter.chapter_id AND exp.owner_profile_id = chapter.owner_profile_id
            LEFT JOIN dbo.career_education AS edu WITH (HOLDLOCK)
              ON edu.chapter_id = chapter.chapter_id AND edu.owner_profile_id = chapter.owner_profile_id
            LEFT JOIN dbo.career_credentials AS cred WITH (HOLDLOCK)
              ON cred.chapter_id = chapter.chapter_id AND cred.owner_profile_id = chapter.owner_profile_id
            LEFT JOIN dbo.career_skills AS skill WITH (HOLDLOCK)
              ON skill.owner_profile_id = policy.owner_profile_id
             AND skill.skill_key = policy.canonical_key
            LEFT JOIN dbo.career_achievements AS ach WITH (HOLDLOCK)
              ON ach.owner_profile_id = policy.owner_profile_id
             AND ach.achievement_key = policy.canonical_key
            LEFT JOIN dbo.career_projects AS proj WITH (HOLDLOCK)
              ON proj.chapter_id = chapter.chapter_id AND proj.owner_profile_id = chapter.owner_profile_id
            LEFT JOIN dbo.entry_policy_records AS parent
              ON parent.owner_profile_id = policy.owner_profile_id
             AND parent.entry_key = policy.parent_entry_key
            WHERE policy.owner_profile_id = @ProfileId
              AND policy.entry_key = @EntryKey
            FOR JSON PATH, WITHOUT_ARRAY_WRAPPER
        );
        EXEC dbo.usp_ResumePublicationEncodeSourceInternal @FieldsJson=@Fields,@Bytes=@Bytes OUTPUT,@Digest=@Digest OUTPUT;
        DECLARE @EvidenceBytes varbinary(max)=@Bytes,@EvidenceDigest char(64)=@Digest,
            @EvidenceKey nvarchar(200)=CONCAT(N''candidate:'',@EntryKey,N'':'',@ContentVersion,N'':'',@Access,N'':'',@Digest),
            @EvidenceVersion int=@ContentVersion,@EvidenceDisplay bit=@Display,@EvidenceAi bit=@Ai,
            @EvidenceContent int=@ContentVersion,@EvidenceAccess int=@Access,@Codec nvarchar(80)=N''resume-canonical-source.v1'',
            @Token nvarchar(100)=CONVERT(nvarchar(100),@ContentVersion);
        IF @OwnerPreview=0
        BEGIN
            DECLARE @Member nvarchar(max);
            SELECT @Member=[value] FROM OPENJSON(@Visitor) WHERE TRY_CONVERT(uniqueidentifier,[key])=@EntryKey;
            IF JSON_VALUE(@Member,''$.evidence_sha256'')<>@Digest OR JSON_VALUE(@Member,''$.canonical_token'')<>@Token
               OR JSON_VALUE(@Member,''$.evidence_sha256'') IS NULL OR JSON_VALUE(@Member,''$.canonical_token'') IS NULL
                THROW 54201, ''AI source authority is unavailable.'', 1;
            SET @EvidenceKey=NULL;
            SELECT TOP (1) @EvidenceKey=evidence_version_key,@EvidenceBytes=content_bytes,@EvidenceDigest=content_sha256,
                @EvidenceDisplay=display_eligible,@EvidenceAi=visitor_ai_eligible,
                @EvidenceContent=policy_content_version,@EvidenceAccess=access_revision,@Codec=codec,@Token=canonical_token
                FROM dbo.resume_publication_evidence WITH (HOLDLOCK)
                WHERE owner_profile_id=@ProfileId AND entry_key=@EntryKey AND content_sha256=@Digest
                  AND policy_content_version=@ContentVersion AND access_revision=@Access AND visitor_ai_eligible=1
                ORDER BY evidence_id DESC;
            IF @EvidenceKey IS NULL OR @EvidenceBytes<>@Bytes OR @EvidenceDigest<>@Digest
                THROW 54201, ''AI source authority is unavailable.'', 1;
            SET @EvidenceVersion=TRY_CONVERT(int,RIGHT(@EvidenceKey,CHARINDEX(N'':'',REVERSE(@EvidenceKey))-1));
            IF @EvidenceVersion IS NULL OR @EvidenceVersion<1 THROW 54201, ''AI source authority is unavailable.'', 1;
        END;
        INSERT @Entries VALUES(@EntryKey,(SELECT @Subject owner_key,CONVERT(nvarchar(36),@EntryKey) entry_key,
            @CanonicalType canonical_type,@ContentVersion content_version,@Access access_revision,
            @Display resume_display,@Ai visitor_ai,N''active'' lifecycle,@CanonicalRevision canonical_revision,
            JSON_QUERY(CONCAT(N''["'',STRING_ESCAPE(@ParentVersion,''json''),N''"]'')) dependency_versions,
            CONVERT(varchar(max),@EvidenceBytes,2) content_hex,@EvidenceDigest content_sha256,@Digest current_content_sha256,
            @EvidenceKey evidence_version_key,@EvidenceVersion evidence_version,@Codec codec,@Token canonical_token,
            @EvidenceContent evidence_content_version,@EvidenceAccess evidence_access_revision,
            @EvidenceDisplay evidence_display,@EvidenceAi evidence_ai FOR JSON PATH,WITHOUT_ARRAY_WRAPPER,INCLUDE_NULL_VALUES));
        FETCH NEXT FROM entry_cursor INTO @EntryKey,@CanonicalType,@ContentVersion,@Access,@Display,@Ai,@CanonicalKey,@Parent;
    END;
    CLOSE entry_cursor; DEALLOCATE entry_cursor;
    DECLARE @PlacementJson nvarchar(max);
    SELECT @PlacementJson=(SELECT slot,source_kind,asset_id,asset_version,asset_digest,presentation_version,
        crop_x,crop_y,crop_width,crop_height,alt_text,decorative,caption
        FROM dbo.resume_media_placements WITH (UPDLOCK,HOLDLOCK) WHERE owner_profile_id=@ProfileId
        ORDER BY slot FOR JSON PATH,INCLUDE_NULL_VALUES);
    DECLARE @Refs table(slot nvarchar(40) PRIMARY KEY,kind nvarchar(40),asset nvarchar(120),version bigint,digest char(64),placement int);
    IF @OwnerPreview=1
        INSERT @Refs SELECT slot,source_kind,asset_id,asset_version,asset_digest,presentation_version
        FROM dbo.resume_media_placements WHERE owner_profile_id=@ProfileId;
    ELSE
    BEGIN
        IF EXISTS(SELECT [key] FROM OPENJSON(@Media) GROUP BY [key] HAVING COUNT(*)<>1)
            THROW 54201, ''AI source authority is unavailable.'', 1;
        IF EXISTS(SELECT 1 FROM OPENJSON(@Media) WHERE JSON_VALUE([value],''$.active'') IS NULL OR JSON_VALUE([value],''$.active'') NOT IN (''true'',''false'',''0'',''1''))
            THROW 54201, ''AI source authority is unavailable.'', 1;
        INSERT @Refs SELECT [key],JSON_VALUE([value],''$.source_kind''),JSON_VALUE([value],''$.source_key''),
            TRY_CONVERT(bigint,JSON_VALUE([value],''$.asset_version'')),JSON_VALUE([value],''$.content_sha256''),
            @Current FROM OPENJSON(@Media)
            WHERE JSON_VALUE([value],''$.active'') IN (''true'',''1'');
    END;
    IF EXISTS(SELECT 1 FROM @Refs WHERE slot NOT IN (''story_banner'',''experience_support'')
        OR kind IS NULL OR kind NOT IN (''owner_photo'',''generated_illustration'') OR asset IS NULL OR version IS NULL OR digest IS NULL OR placement IS NULL)
        THROW 54201, ''AI source authority is unavailable.'', 1;
    DECLARE @MediaRows table(slot nvarchar(40) PRIMARY KEY,payload nvarchar(max));
    DECLARE @Slot nvarchar(40),@Kind nvarchar(40),@Asset nvarchar(120),@Version bigint,@AssetDigest char(64),@Placement int;
    DECLARE media_cursor CURSOR LOCAL FAST_FORWARD FOR SELECT slot,kind,asset,version,digest,placement FROM @Refs ORDER BY slot;
    OPEN media_cursor; FETCH NEXT FROM media_cursor INTO @Slot,@Kind,@Asset,@Version,@AssetDigest,@Placement;
    WHILE @@FETCH_STATUS=0
    BEGIN
        DECLARE @SourceRevision nvarchar(100)=NULL,@CatalogRevision nvarchar(100)=NULL,@ReadyJson nvarchar(max)=NULL;
        IF @Kind=N''generated_illustration''
        BEGIN
            SELECT @SourceRevision=CONVERT(nvarchar(100),asset_version),@CatalogRevision=CONVERT(nvarchar(100),asset_version),
                @ReadyJson=(SELECT asset_version,content_sha256,lifecycle,origin,width,height FOR JSON PATH,WITHOUT_ARRAY_WRAPPER)
                FROM dbo.resume_catalog_assets WITH (UPDLOCK,HOLDLOCK)
                WHERE asset_id=TRY_CONVERT(uniqueidentifier,@Asset) AND asset_version=@Version AND content_sha256=@AssetDigest AND lifecycle=N''active'';
        END
        ELSE
        BEGIN
            SELECT @SourceRevision=CONVERT(varchar(16),row_version,2),
                @ReadyJson=(SELECT CONVERT(varchar(16),row_version,2) version,state,scan_result,
                    CONVERT(varchar(64),derivative_sha256_digest,2) digest,pixel_width,pixel_height FOR JSON PATH,WITHOUT_ARRAY_WRAPPER)
                FROM dbo.capture_media_sources WITH (HOLDLOCK)
                WHERE owner_profile_id=@ProfileId AND source_key=TRY_CONVERT(uniqueidentifier,@Asset)
                  AND CONVERT(bigint,row_version)=@Version AND state IN (N''needs_review'',N''confirmed'') AND scan_result=N''clean''
                  AND LOWER(CONVERT(varchar(64),derivative_sha256_digest,2))=@AssetDigest AND deleted_at_utc IS NULL;
        END;
        IF @SourceRevision IS NULL OR @ReadyJson IS NULL THROW 54201, ''AI source authority is unavailable.'', 1;
        INSERT @MediaRows VALUES(@Slot,(SELECT @Slot slot,@Placement placement_version,@Kind source_kind,@Asset source_key,
            @SourceRevision source_revision,@Version asset_version,@CatalogRevision catalog_revision,@AssetDigest content_sha256,
            LOWER(CONVERT(char(64),HASHBYTES(''SHA2_256'',dbo.fn_ResumePublicationUtf8(@ReadyJson)),2)) readiness_sha256,
            CONVERT(bit,1) ready,CONVERT(bit,1) active FOR JSON PATH,WITHOUT_ARRAY_WRAPPER,INCLUDE_NULL_VALUES));
        FETCH NEXT FROM media_cursor INTO @Slot,@Kind,@Asset,@Version,@AssetDigest,@Placement;
    END;
    CLOSE media_cursor; DEALLOCATE media_cursor;
    DECLARE @EntriesJson nvarchar(max),@MediaJson nvarchar(max),@Snapshot nvarchar(max);
    SELECT @EntriesJson=N''[''+COALESCE(STRING_AGG(CONVERT(nvarchar(max),payload),N'','') WITHIN GROUP(ORDER BY entry_key),N'''')+N'']'' FROM @Entries;
    SELECT @MediaJson=N''[''+COALESCE(STRING_AGG(CONVERT(nvarchar(max),payload),N'','') WITHIN GROUP(ORDER BY slot),N'''')+N'']'' FROM @MediaRows;
    SELECT @Snapshot=(SELECT 1 schema_version,@Subject subject_key,CONCAT(N''resume:'',@Subject) resume_key,
        CASE WHEN @OwnerPreview=1 THEN N''owner_preview'' ELSE N''guest'' END mode,
        @ProfileVersion profile_revision,@Sharing sharing_enabled,@Epoch sharing_epoch,@Revision publication_revision,
        @Current current_revision,@Reviewed reviewed_digest,@Draft draft_revision,
        LOWER(CONVERT(char(64),HASHBYTES(''SHA2_256'',dbo.fn_ResumePublicationUtf8(@DraftJson)),2)) draft_digest,
        LOWER(CONVERT(char(64),HASHBYTES(''SHA2_256'',dbo.fn_ResumePublicationUtf8(@PlacementJson)),2)) placement_digest,
        JSON_QUERY(@EntriesJson) entries,JSON_QUERY(@MediaJson) media,JSON_QUERY(@Media) publication_media
        FOR JSON PATH,WITHOUT_ARRAY_WRAPPER,INCLUDE_NULL_VALUES);
    COMMIT TRANSACTION;
    SELECT @Snapshot snapshot_json;
    END TRY
    BEGIN CATCH
        IF XACT_STATE()<>0 ROLLBACK TRANSACTION;
        THROW;
    END CATCH;
END;';

    EXEC sys.sp_executesql N'CREATE OR ALTER PROCEDURE dbo.usp_GetOwnerLivingResumeEditor
            @UserKey nvarchar(300)
        AS
        BEGIN
            SET NOCOUNT ON;
            SET XACT_ABORT ON;

            DECLARE @ProfileId bigint;
            SELECT @ProfileId = profile.profile_id
            FROM dbo.member_profiles AS profile
            JOIN dbo.app_users AS app_user ON app_user.id = profile.user_id
            WHERE app_user.user_key = @UserKey
              AND app_user.active = 1
              AND profile.active = 1;

            IF @ProfileId IS NULL
                THROW 52002, ''RESUME_EDITOR_NOT_FOUND'', 1;

            SELECT profile.profile_key, profile.profile_slug, profile.display_name
            FROM dbo.member_profiles AS profile
            WHERE profile.profile_id = @ProfileId;

            SELECT
                chapter.chapter_key AS record_key,
                experience.role_title,
                experience.employer_name,
                chapter.location_text,
                chapter.summary,
                chapter.start_date,
                chapter.end_date,
                chapter.date_precision,
                experience.employment_type,
                experience.current_role,
                chapter.row_version,
                CONVERT(bit, CASE WHEN
                    chapter.visibility = N''private''
                    AND chapter.approval_status = N''draft''
                    AND chapter.publication_status = N''unpublished''
                    AND entity.visibility = N''private''
                    AND entity.approval_status = N''draft''
                    AND entity.publication_status = N''unpublished''
                    AND NOT EXISTS (SELECT 1 FROM dbo.entity_publication_versions AS publication WHERE publication.entity_id = entity.entity_id)
                    AND NOT EXISTS (SELECT 1 FROM dbo.entity_access_grants AS grant_row WHERE grant_row.entity_id = entity.entity_id)
                    AND NOT EXISTS (SELECT 1 FROM dbo.content_approval_events AS history WHERE history.entity_id = entity.entity_id)
                    THEN 1 ELSE 0 END) AS editable,
                CASE WHEN
                    chapter.visibility <> N''private'' OR chapter.approval_status <> N''draft'' OR chapter.publication_status <> N''unpublished''
                    OR entity.visibility <> N''private'' OR entity.approval_status <> N''draft'' OR entity.publication_status <> N''unpublished''
                    OR EXISTS (SELECT 1 FROM dbo.entity_publication_versions AS publication WHERE publication.entity_id = entity.entity_id)
                    OR EXISTS (SELECT 1 FROM dbo.entity_access_grants AS grant_row WHERE grant_row.entity_id = entity.entity_id)
                    OR EXISTS (SELECT 1 FROM dbo.content_approval_events AS history WHERE history.entity_id = entity.entity_id)
                    THEN N''published_or_history_bearing'' ELSE NULL END AS blocked_reason
            FROM dbo.career_chapters AS chapter
            JOIN dbo.career_experiences AS experience
              ON experience.chapter_id = chapter.chapter_id
             AND experience.owner_profile_id = chapter.owner_profile_id
            JOIN dbo.slate_entities AS entity
              ON entity.entity_id = chapter.entity_id
             AND entity.owner_profile_id = chapter.owner_profile_id
            WHERE chapter.owner_profile_id = @ProfileId
              AND chapter.chapter_type = N''experience''
              AND chapter.deleted_at_utc IS NULL
              AND entity.active = 1
              AND entity.deleted_at_utc IS NULL
            ORDER BY chapter.display_order, chapter.start_date, chapter.chapter_id;

            SELECT
                achievement.achievement_key AS record_key,
                chapter.chapter_key AS parent_key,
                achievement.original_member_wording AS wording,
                achievement.metric_value,
                achievement.metric_label,
                achievement.row_version,
                CONVERT(bit, CASE WHEN
                    achievement.visibility = N''private'' AND achievement.approval_status = N''draft''
                    AND entity.visibility = N''private'' AND entity.approval_status = N''draft''
                    AND entity.publication_status = N''unpublished''
                    AND NOT EXISTS (SELECT 1 FROM dbo.entity_publication_versions AS publication WHERE publication.entity_id = entity.entity_id)
                    AND NOT EXISTS (SELECT 1 FROM dbo.entity_access_grants AS grant_row WHERE grant_row.entity_id = entity.entity_id)
                    AND NOT EXISTS (SELECT 1 FROM dbo.content_approval_events AS history WHERE history.entity_id = entity.entity_id)
                    THEN 1 ELSE 0 END) AS editable,
                CASE WHEN
                    achievement.visibility <> N''private'' OR achievement.approval_status <> N''draft''
                    OR entity.visibility <> N''private'' OR entity.approval_status <> N''draft'' OR entity.publication_status <> N''unpublished''
                    OR EXISTS (SELECT 1 FROM dbo.entity_publication_versions AS publication WHERE publication.entity_id = entity.entity_id)
                    OR EXISTS (SELECT 1 FROM dbo.entity_access_grants AS grant_row WHERE grant_row.entity_id = entity.entity_id)
                    OR EXISTS (SELECT 1 FROM dbo.content_approval_events AS history WHERE history.entity_id = entity.entity_id)
                    THEN N''published_or_history_bearing'' ELSE NULL END AS blocked_reason
            FROM dbo.career_achievements AS achievement
            JOIN dbo.career_chapters AS chapter
              ON chapter.chapter_id = achievement.chapter_id
             AND chapter.owner_profile_id = achievement.owner_profile_id
            JOIN dbo.slate_entities AS entity
              ON entity.entity_id = achievement.entity_id
             AND entity.owner_profile_id = achievement.owner_profile_id
            WHERE achievement.owner_profile_id = @ProfileId
              AND achievement.deleted_at_utc IS NULL
              AND entity.active = 1
              AND entity.deleted_at_utc IS NULL
            ORDER BY chapter.display_order, achievement.display_order, achievement.achievement_id;

            SELECT
                skill.skill_key AS record_key,
                skill.skill_name AS name,
                skill.skill_summary AS summary,
                skill.row_version,
                CONVERT(bit, CASE WHEN
                    skill.visibility = N''private'' AND skill.approval_status = N''draft''
                    AND entity.visibility = N''private'' AND entity.approval_status = N''draft''
                    AND entity.publication_status = N''unpublished''
                    AND NOT EXISTS (SELECT 1 FROM dbo.entity_publication_versions AS publication WHERE publication.entity_id = entity.entity_id)
                    AND NOT EXISTS (SELECT 1 FROM dbo.entity_access_grants AS grant_row WHERE grant_row.entity_id = entity.entity_id)
                    AND NOT EXISTS (SELECT 1 FROM dbo.content_approval_events AS history WHERE history.entity_id = entity.entity_id)
                    THEN 1 ELSE 0 END) AS editable,
                CASE WHEN
                    skill.visibility <> N''private'' OR skill.approval_status <> N''draft''
                    OR entity.visibility <> N''private'' OR entity.approval_status <> N''draft'' OR entity.publication_status <> N''unpublished''
                    OR EXISTS (SELECT 1 FROM dbo.entity_publication_versions AS publication WHERE publication.entity_id = entity.entity_id)
                    OR EXISTS (SELECT 1 FROM dbo.entity_access_grants AS grant_row WHERE grant_row.entity_id = entity.entity_id)
                    OR EXISTS (SELECT 1 FROM dbo.content_approval_events AS history WHERE history.entity_id = entity.entity_id)
                    THEN N''published_or_history_bearing'' ELSE NULL END AS blocked_reason
            FROM dbo.career_skills AS skill
            JOIN dbo.slate_entities AS entity
              ON entity.entity_id = skill.entity_id
             AND entity.owner_profile_id = skill.owner_profile_id
            WHERE skill.owner_profile_id = @ProfileId
              AND skill.deleted_at_utc IS NULL
              AND entity.active = 1
              AND entity.deleted_at_utc IS NULL
            ORDER BY skill.featured DESC, skill.display_order, skill.skill_name;

            SELECT
                chapter.chapter_key AS record_key,
                credential.credential_name AS name,
                credential.issuer_name AS issuer,
                credential.credential_identifier AS identifier,
                credential.issue_date,
                credential.expiration_date,
                credential.verification_url,
                credential.credential_completion_status AS completion_status,
                chapter.row_version,
                CONVERT(bit, CASE WHEN
                    chapter.visibility = N''private'' AND chapter.approval_status = N''draft''
                    AND chapter.publication_status = N''unpublished''
                    AND entity.visibility = N''private'' AND entity.approval_status = N''draft''
                    AND entity.publication_status = N''unpublished''
                    AND NOT EXISTS (SELECT 1 FROM dbo.entity_publication_versions AS publication WHERE publication.entity_id = entity.entity_id)
                    AND NOT EXISTS (SELECT 1 FROM dbo.entity_access_grants AS grant_row WHERE grant_row.entity_id = entity.entity_id)
                    AND NOT EXISTS (SELECT 1 FROM dbo.content_approval_events AS history WHERE history.entity_id = entity.entity_id)
                    THEN 1 ELSE 0 END) AS editable,
                CASE WHEN
                    chapter.visibility <> N''private'' OR chapter.approval_status <> N''draft'' OR chapter.publication_status <> N''unpublished''
                    OR entity.visibility <> N''private'' OR entity.approval_status <> N''draft'' OR entity.publication_status <> N''unpublished''
                    OR EXISTS (SELECT 1 FROM dbo.entity_publication_versions AS publication WHERE publication.entity_id = entity.entity_id)
                    OR EXISTS (SELECT 1 FROM dbo.entity_access_grants AS grant_row WHERE grant_row.entity_id = entity.entity_id)
                    OR EXISTS (SELECT 1 FROM dbo.content_approval_events AS history WHERE history.entity_id = entity.entity_id)
                    THEN N''published_or_history_bearing'' ELSE NULL END AS blocked_reason
            FROM dbo.career_chapters AS chapter
            JOIN dbo.career_credentials AS credential
              ON credential.chapter_id = chapter.chapter_id
             AND credential.owner_profile_id = chapter.owner_profile_id
            JOIN dbo.slate_entities AS entity
              ON entity.entity_id = chapter.entity_id
             AND entity.owner_profile_id = chapter.owner_profile_id
            WHERE chapter.owner_profile_id = @ProfileId
              AND chapter.chapter_type = N''credential''
              AND chapter.deleted_at_utc IS NULL
              AND entity.active = 1
              AND entity.deleted_at_utc IS NULL
            ORDER BY chapter.display_order, credential.issue_date, chapter.chapter_id;
            SELECT
                chapter.chapter_key AS record_key,
                chapter.title,
                education.institution_name,
                education.degree_name,
                education.field_of_study,
                education.education_status,
                education.grade_text,
                chapter.location_text,
                chapter.summary,
                chapter.start_date,
                chapter.end_date,
                chapter.date_precision,
                chapter.row_version,
                CONVERT(bit, CASE WHEN
                    chapter.visibility = N''private''
                    AND chapter.approval_status = N''draft''
                    AND chapter.publication_status = N''unpublished''
                    AND entity.visibility = N''private''
                    AND entity.approval_status = N''draft''
                    AND entity.publication_status = N''unpublished''
                    AND NOT EXISTS (SELECT 1 FROM dbo.entity_publication_versions AS publication WHERE publication.entity_id = entity.entity_id)
                    AND NOT EXISTS (SELECT 1 FROM dbo.entity_access_grants AS grant_row WHERE grant_row.entity_id = entity.entity_id)
                    AND NOT EXISTS (SELECT 1 FROM dbo.content_approval_events AS history WHERE history.entity_id = entity.entity_id)
                    THEN 1 ELSE 0 END) AS editable,
                CASE WHEN
                    chapter.visibility <> N''private'' OR chapter.approval_status <> N''draft'' OR chapter.publication_status <> N''unpublished''
                    OR entity.visibility <> N''private'' OR entity.approval_status <> N''draft'' OR entity.publication_status <> N''unpublished''
                    OR EXISTS (SELECT 1 FROM dbo.entity_publication_versions AS publication WHERE publication.entity_id = entity.entity_id)
                    OR EXISTS (SELECT 1 FROM dbo.entity_access_grants AS grant_row WHERE grant_row.entity_id = entity.entity_id)
                    OR EXISTS (SELECT 1 FROM dbo.content_approval_events AS history WHERE history.entity_id = entity.entity_id)
                    THEN N''published_or_history_bearing'' ELSE NULL END AS blocked_reason
            FROM dbo.career_chapters AS chapter
            JOIN dbo.career_education AS education
              ON education.chapter_id = chapter.chapter_id
             AND education.owner_profile_id = chapter.owner_profile_id
            JOIN dbo.slate_entities AS entity
              ON entity.entity_id = chapter.entity_id
             AND entity.owner_profile_id = chapter.owner_profile_id
            WHERE chapter.owner_profile_id = @ProfileId
              AND chapter.chapter_type = N''education''
              AND chapter.deleted_at_utc IS NULL
              AND entity.active = 1
              AND entity.deleted_at_utc IS NULL
            ORDER BY chapter.display_order, chapter.start_date, chapter.chapter_id;

        END;';

    IF COL_LENGTH(N'dbo.resume_drafts',N'story_entry_key') IS NOT NULL
        ALTER TABLE dbo.resume_drafts DROP COLUMN story_entry_key;
    ALTER TABLE dbo.resume_draft_items DROP CONSTRAINT CK_resume_draft_items_type;
    ALTER TABLE dbo.resume_draft_items ADD CONSTRAINT CK_resume_draft_items_type CHECK
      (record_type IN(N'role',N'education',N'credential',N'skill',N'accomplishment'));
    ALTER TABLE dbo.resume_draft_command_receipts DROP CONSTRAINT CK_resume_draft_command_receipts_type;
    ALTER TABLE dbo.resume_draft_command_receipts ADD CONSTRAINT CK_resume_draft_command_receipts_type CHECK
      (command_type IN(N'save_item',N'discard_item',N'create_private_item',N'review_candidate'));
    ALTER TABLE dbo.resume_draft_command_receipts DROP CONSTRAINT CK_resume_draft_command_receipts_outcome;
    ALTER TABLE dbo.resume_draft_command_receipts ADD CONSTRAINT CK_resume_draft_command_receipts_outcome CHECK
      (outcome IN(N'saved',N'discarded',N'created',N'reviewed'));

    EXEC sys.sp_executesql N'CREATE OR ALTER PROCEDURE dbo.usp_ResumePublicationRefreshProjectionInternal
    @ProfileId bigint,
    @Revision int,
    @Digest char(64),
    @Display nvarchar(max),
    @VisitorAi nvarchar(max),
    @Evidence nvarchar(max),
    @Media nvarchar(max)
AS
BEGIN
    SET NOCOUNT ON;
    SET XACT_ABORT ON;
    SET @Display = ISNULL(@Display, N''{}'');
    SET @VisitorAi = ISNULL(@VisitorAi, N''{}'');
    SET @Evidence = ISNULL(@Evidence, N''{}'');
    SET @Media = ISNULL(@Media, N''{}'');
    INSERT dbo.resume_publication_revisions
        (owner_profile_id, publication_revision, reviewed_digest, display_json, visitor_ai_json, evidence_json, media_json)
    VALUES (@ProfileId, @Revision, @Digest, @Display, @VisitorAi, @Evidence, @Media);
    UPDATE dbo.resume_sharing_state
       SET publication_revision = @Revision,
           current_revision = @Revision,
           updated_at_utc = SYSUTCDATETIME()
     WHERE owner_profile_id = @ProfileId;
END;';

    EXEC sys.sp_executesql N'CREATE OR ALTER PROCEDURE dbo.usp_CommitResumePublicationCommandForOwner
    @UserKey nvarchar(300),
    @RequestId uniqueidentifier,
    @CommandJson nvarchar(max)
AS
BEGIN
    SET NOCOUNT ON;
    SET XACT_ABORT ON;
    SET TRANSACTION ISOLATION LEVEL SERIALIZABLE;
    IF @@TRANCOUNT <> 0
        THROW 54020, ''Ambient transactions are not permitted.'', 1;
    BEGIN TRANSACTION;

    DECLARE @ProfileId bigint;
    SELECT @ProfileId = profile.profile_id
      FROM dbo.member_profiles AS profile WITH (UPDLOCK, HOLDLOCK)
      JOIN dbo.app_users AS app_user ON app_user.id = profile.user_id
     WHERE app_user.user_key = @UserKey
       AND app_user.active = 1
       AND profile.active = 1;
    IF @ProfileId IS NULL
        THROW 54021, ''Owner is unavailable.'', 1;

    EXEC dbo.usp_ResumePublicationLockOwnerInternal @ProfileId = @ProfileId;

    DECLARE @Type nvarchar(40) = JSON_VALUE(@CommandJson, ''$.type'');
    IF @Type NOT IN (
            N''publish'', N''correct'', N''change_permissions'', N''delete'', N''restore'',
            N''sharing_off'', N''catalog_withdraw'', N''media_restrict'',
            N''create'', N''edit'', N''recategorize'', N''permanently_delete'', N''resolve_match'')
        THROW 54025, ''Unknown publication command.'', 1;

    DECLARE @Digest char(64) = LOWER(CONVERT(char(64), HASHBYTES(''SHA2_256'', dbo.fn_ResumePublicationUtf8(@CommandJson)), 2));
    DECLARE @Existing char(64), @ExistingOutcome nvarchar(40);
    SELECT @Existing = request_digest, @ExistingOutcome = outcome
      FROM dbo.resume_publication_receipts WITH (UPDLOCK, HOLDLOCK)
     WHERE owner_profile_id = @ProfileId AND request_id = @RequestId;
    IF @Existing IS NOT NULL
    BEGIN
        IF @Existing <> @Digest
            THROW 54022, ''That request already used a different payload.'', 1;
        SELECT committed = CONVERT(bit, 1), replayed = CONVERT(bit, 1), outcome = @ExistingOutcome,
               request_digest = @Existing, read_state = N''current'';
        COMMIT;
        RETURN;
    END;

    DECLARE @PublicationRevision int, @CurrentRevision int, @Sharing bit;
    SELECT @PublicationRevision = publication_revision,
           @CurrentRevision = current_revision, @Sharing = sharing_enabled
      FROM dbo.resume_sharing_state WITH (UPDLOCK, HOLDLOCK)
     WHERE owner_profile_id = @ProfileId;

    DECLARE @Expected int = TRY_CONVERT(int, JSON_VALUE(@CommandJson, ''$.expected_publication_revision''));
    IF @Expected IS NOT NULL AND @Expected <> @PublicationRevision
        THROW 54023, ''The publication changed.'', 1;

    DECLARE @NewRevision int = @PublicationRevision;
    DECLARE @Outcome nvarchar(40) = N''applied'';
    DECLARE @Display nvarchar(max), @Visitor nvarchar(max), @Evidence nvarchar(max), @Media nvarchar(max);

    IF @Type IN (N''create'', N''edit'', N''recategorize'', N''permanently_delete'', N''resolve_match'',
                 N''change_permissions'', N''delete'', N''restore'', N''correct'')
    BEGIN
        IF @Type IN (N''edit'', N''correct'', N''change_permissions'')
            EXEC dbo.usp_ResumePublicationApplyCanonicalInternal @ProfileId = @ProfileId, @CommandJson = @CommandJson;
        ELSE IF OBJECT_ID(N''dbo.usp_CommitEntryPolicyCommandForOwnerCore'', N''P'') IS NOT NULL
            EXEC dbo.usp_CommitEntryPolicyCommandForOwnerCore
                @UserKey = @UserKey, @RequestId = @RequestId, @CommandJson = @CommandJson;
        ELSE
            EXEC dbo.usp_ResumePublicationApplyCanonicalInternal @ProfileId = @ProfileId, @CommandJson = @CommandJson;
        IF @Type = N''restore''
        BEGIN
            SET @Outcome = N''restored_private'';
        END
        ELSE IF @CurrentRevision IS NOT NULL AND @Type <> N''create''
        BEGIN
            SET @NewRevision = @PublicationRevision + 1;
            EXEC dbo.usp_ResumePublicationBuildManifestsInternal
                @ProfileId = @ProfileId, @Revision = @NewRevision, @CommandJson = @CommandJson,
                @Display = @Display OUTPUT, @VisitorAi = @Visitor OUTPUT, @Evidence = @Evidence OUTPUT;
            SELECT @Media = media_json
              FROM dbo.resume_publication_revisions WITH (UPDLOCK, HOLDLOCK)
             WHERE owner_profile_id = @ProfileId AND publication_revision = @CurrentRevision;
            EXEC dbo.usp_ResumePublicationRefreshProjectionInternal
                @ProfileId = @ProfileId, @Revision = @NewRevision, @Digest = @Digest,
                @Display = @Display, @VisitorAi = @Visitor,
                @Evidence = @Evidence, @Media = @Media;
            SET @Outcome = CASE @Type WHEN N''correct'' THEN N''corrected'' WHEN N''edit'' THEN N''corrected''
                                      WHEN N''delete'' THEN N''deleted'' ELSE N''restricted'' END;
        END
        ELSE
            SET @Outcome = CASE @Type WHEN N''create'' THEN N''created'' ELSE N''applied'' END;
    END
    ELSE IF @Type = N''publish''
    BEGIN
        DECLARE @Reviewed char(64) = JSON_VALUE(@CommandJson, ''$.reviewed_digest'');
        IF @Reviewed IS NULL OR LEN(@Reviewed) <> 64
            THROW 54024, ''Reviewed digest is required.'', 1;
        SET @NewRevision = @PublicationRevision + 1;
        SET @Outcome = N''published'';
        UPDATE dbo.resume_sharing_state
           SET sharing_enabled = 1, sharing_epoch = sharing_epoch + 1,
               public_slug = JSON_VALUE(@CommandJson, ''$.slug''),
               updated_at_utc = SYSUTCDATETIME()
         WHERE owner_profile_id = @ProfileId;
        EXEC dbo.usp_ResumePublicationBuildManifestsInternal
            @ProfileId = @ProfileId, @Revision = @NewRevision, @CommandJson = @CommandJson,
            @Display = @Display OUTPUT, @VisitorAi = @Visitor OUTPUT, @Evidence = @Evidence OUTPUT;
        SET @Media = ISNULL(JSON_QUERY(@CommandJson, ''$.media''), N''{}'');
        IF ISJSON(@Media) <> 1 SET @Media = N''{}'';
        EXEC dbo.usp_ResumePublicationRefreshProjectionInternal
            @ProfileId = @ProfileId, @Revision = @NewRevision, @Digest = @Reviewed,
            @Display = @Display, @VisitorAi = @Visitor,
            @Evidence = @Evidence, @Media = @Media;
    END
    ELSE IF @Type = N''sharing_off''
    BEGIN
        SET @Outcome = N''restricted'';
        UPDATE dbo.resume_sharing_state
           SET sharing_enabled = 0, sharing_epoch = sharing_epoch + 1, updated_at_utc = SYSUTCDATETIME()
         WHERE owner_profile_id = @ProfileId;
    END
    ELSE IF @Type = N''catalog_withdraw''
    BEGIN
        SET @Outcome = N''withdrawn'';
        DECLARE @WithdrawAssetId uniqueidentifier = TRY_CONVERT(uniqueidentifier, JSON_VALUE(@CommandJson, ''$.asset_id''));
        DECLARE @WithdrawAssetVersion int = TRY_CONVERT(int, JSON_VALUE(@CommandJson, ''$.version''));
        EXEC dbo.usp_ResumeCatalogApplyInternal
            @AssetId = @WithdrawAssetId,
            @AssetVersion = @WithdrawAssetVersion,
            @Lifecycle = N''withdrawn'';
        SET @NewRevision = @PublicationRevision + 1;
        SELECT @Display = display_json, @Visitor = visitor_ai_json, @Evidence = evidence_json, @Media = media_json
          FROM dbo.resume_publication_revisions WITH (UPDLOCK, HOLDLOCK)
         WHERE owner_profile_id = @ProfileId AND publication_revision = @CurrentRevision;
        EXEC dbo.usp_ResumePublicationRefreshProjectionInternal
            @ProfileId = @ProfileId, @Revision = @NewRevision, @Digest = @Digest,
            @Display = @Display, @VisitorAi = @Visitor,
            @Evidence = @Evidence, @Media = @Media;
    END
    ELSE IF @Type = N''media_restrict''
    BEGIN
        SET @Outcome = N''restricted'';
        SET @NewRevision = @PublicationRevision + 1;
        SELECT @Display = display_json, @Visitor = visitor_ai_json, @Evidence = evidence_json, @Media = media_json
          FROM dbo.resume_publication_revisions WITH (UPDLOCK, HOLDLOCK)
         WHERE owner_profile_id = @ProfileId AND publication_revision = @CurrentRevision;
        DECLARE @Slot nvarchar(40) = JSON_VALUE(@CommandJson, ''$.slot'');
        IF @Media IS NOT NULL AND @Slot IS NOT NULL
            SET @Media = JSON_MODIFY(@Media, CONCAT(N''$."'', @Slot, N''".active''), CONVERT(bit, 0));
        EXEC dbo.usp_ResumePublicationRefreshProjectionInternal
            @ProfileId = @ProfileId, @Revision = @NewRevision, @Digest = @Digest,
            @Display = @Display, @VisitorAi = @Visitor,
            @Evidence = @Evidence, @Media = @Media;
    END;

    INSERT dbo.resume_publication_receipts (owner_profile_id, request_id, request_digest, command_type, outcome)
    VALUES (@ProfileId, @RequestId, @Digest, @Type, @Outcome);
    INSERT dbo.resume_publication_outbox (owner_profile_id, publication_revision, event_type, payload_json)
    VALUES (@ProfileId, @NewRevision, @Type, @CommandJson);

    SELECT committed = CONVERT(bit, 1), replayed = CONVERT(bit, 0), outcome = @Outcome,
           request_digest = @Digest, read_state = N''current'', publication_revision = @NewRevision;
    COMMIT;
END;';

    EXEC sys.sp_executesql N'CREATE OR ALTER PROCEDURE dbo.usp_GetResumePublicationForOwner
    @UserKey nvarchar(300)
AS
BEGIN
    SET NOCOUNT ON;
    DECLARE @ProfileId bigint;
    SELECT @ProfileId = profile.profile_id
      FROM dbo.member_profiles AS profile
      JOIN dbo.app_users AS app_user ON app_user.id = profile.user_id
     WHERE app_user.user_key = @UserKey AND app_user.active = 1 AND profile.active = 1;
    SELECT s.sharing_enabled, s.sharing_epoch, s.publication_revision, s.current_revision, s.public_slug,
           r.media_json, r.reviewed_digest
      FROM dbo.resume_sharing_state AS s
      LEFT JOIN dbo.resume_publication_revisions AS r
        ON r.owner_profile_id = s.owner_profile_id
       AND r.publication_revision = s.current_revision
     WHERE s.owner_profile_id = @ProfileId;
END;';

    EXEC sys.sp_executesql N'CREATE OR ALTER PROCEDURE dbo.usp_GetPublicResumePublicationBySlug
    @ProfileSlug nvarchar(100)
AS
BEGIN
    SET NOCOUNT ON;
    DECLARE @ProfileId bigint, @Revision int, @Sharing bit;
    SELECT @ProfileId = owner_profile_id, @Revision = current_revision, @Sharing = sharing_enabled
      FROM dbo.resume_sharing_state
     WHERE public_slug = @ProfileSlug;
    IF @ProfileId IS NULL OR @Sharing = 0 OR @Revision IS NULL
        THROW 54030, ''Publication is unavailable.'', 1;
    SELECT r.publication_revision, r.reviewed_digest, r.display_json, r.media_json
      FROM dbo.resume_publication_revisions AS r
     WHERE r.owner_profile_id = @ProfileId AND r.publication_revision = @Revision;
END;';

    EXEC sys.sp_executesql N'CREATE OR ALTER PROCEDURE dbo.usp_GetResumePublicationMediaAuthorization
    @ProfileSlug nvarchar(100),
    @Slot nvarchar(40),
    @PublicationRevision int = NULL
AS
BEGIN
    SET NOCOUNT ON;
    DECLARE @ProfileId bigint, @Revision int, @Sharing bit, @Media nvarchar(max);
    SELECT @ProfileId = owner_profile_id, @Revision = current_revision, @Sharing = sharing_enabled
      FROM dbo.resume_sharing_state
     WHERE public_slug = @ProfileSlug;
    IF @ProfileId IS NULL OR @Sharing = 0 OR @Revision IS NULL
        THROW 54031, ''Media is unavailable.'', 1;
    IF @PublicationRevision IS NOT NULL AND @PublicationRevision <> @Revision
        THROW 54032, ''Media is unavailable.'', 1;
    SELECT @Media = media_json
      FROM dbo.resume_publication_revisions
     WHERE owner_profile_id = @ProfileId AND publication_revision = @Revision;
    DECLARE @Active bit = TRY_CONVERT(bit, JSON_VALUE(@Media, CONCAT(N''$."'', @Slot, N''".active'')));
    DECLARE @Kind nvarchar(40) = JSON_VALUE(@Media, CONCAT(N''$."'', @Slot, N''".source_kind''));
    DECLARE @SourceKey nvarchar(80) = JSON_VALUE(@Media, CONCAT(N''$."'', @Slot, N''".source_key''));
    DECLARE @AssetVersion int = TRY_CONVERT(int, JSON_VALUE(@Media, CONCAT(N''$."'', @Slot, N''".asset_version'')));
    DECLARE @Digest char(64) = JSON_VALUE(@Media, CONCAT(N''$."'', @Slot, N''".content_sha256''));
    IF @Media IS NULL OR @Active IS NULL OR @Active <> 1
        THROW 54033, ''Media is unavailable.'', 1;
    IF @Kind = N''generated_illustration''
    BEGIN
        IF NOT EXISTS (
            SELECT 1 FROM dbo.resume_catalog_assets
             WHERE CONVERT(nvarchar(36), asset_id) = @SourceKey
               AND asset_version = @AssetVersion
               AND lifecycle = N''active''
               AND content_sha256 = @Digest)
            THROW 54034, ''Media is unavailable.'', 1;
    END;
    SELECT authorized = CONVERT(bit, 1), slot = @Slot, rechecked = CONVERT(bit, 1),
           content_sha256 = @Digest, source_kind = @Kind, source_key = @SourceKey,
           asset_version = @AssetVersion, publication_revision = @Revision;
END;';

    EXEC sys.sp_executesql N'CREATE OR ALTER PROCEDURE dbo.usp_GetCurrentProfilePublicationForOwner
    @OwnerKey nvarchar(300), @Audience nvarchar(20)
  AS
  BEGIN
    SET NOCOUNT ON;
    SELECT revision.manifest_json
    FROM dbo.app_users AS app_user
    JOIN dbo.member_profiles AS profile ON profile.user_id=app_user.id AND profile.active=1
    JOIN dbo.profile_publications AS publication ON publication.owner_profile_id=profile.profile_id AND publication.audience=@Audience AND publication.publication_state=N''published''
    JOIN dbo.profile_publication_revisions AS revision ON revision.profile_publication_revision_id=publication.current_revision_id AND revision.owner_profile_id=profile.profile_id AND revision.audience=@Audience
    WHERE app_user.user_key=@OwnerKey AND app_user.active=1;
  END';

    IF COL_LENGTH(N'dbo.resume_publication_revisions',N'profile_identity_json') IS NOT NULL
    BEGIN
        ALTER TABLE dbo.resume_publication_revisions DROP CONSTRAINT CK_resume_publication_identity_json;
        ALTER TABLE dbo.resume_publication_revisions DROP COLUMN profile_identity_json;
    END;
    IF COL_LENGTH(N'dbo.resume_media_command_receipts',N'catalog_source_bound') IS NOT NULL
    BEGIN
        ALTER TABLE dbo.resume_media_command_receipts DROP CONSTRAINT DF_resume_media_receipts_catalog_bound;
        ALTER TABLE dbo.resume_media_command_receipts DROP COLUMN catalog_source_bound;
    END;
    DELETE dbo.schema_migrations WHERE migration_id=N'PS-RESUME-IDENTITY-001';
    COMMIT;
END TRY
BEGIN CATCH
    IF @@TRANCOUNT > 0 ROLLBACK;
    THROW;
END CATCH;
