/* PS-VISITOR-AI-001. Proposed read-only F eligibility readers over existing E records.
No provider work or new fact store. Application/schema execution requires separate authority. */
SET NOCOUNT ON;
SET XACT_ABORT ON;
BEGIN TRY
BEGIN TRANSACTION;
IF NOT EXISTS(SELECT 1 FROM dbo.schema_migrations WHERE migration_id=N'PS-RESUME-PUBLICATION-001')
    THROW 54200, 'PS-RESUME-PUBLICATION-001 must be applied first.', 1;
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

EXEC sys.sp_executesql N'CREATE OR ALTER PROCEDURE dbo.usp_GetMemberVisitorAiBySlug @ProfileSlug nvarchar(100)
AS BEGIN SET NOCOUNT ON; EXEC dbo.usp_MemberVisitorAiSnapshotInternal @ProfileSlug=@ProfileSlug,@OwnerPreview=0; END;';

EXEC sys.sp_executesql N'CREATE OR ALTER PROCEDURE dbo.usp_GetMemberVisitorAiPreviewForOwner @UserKey nvarchar(300)
AS BEGIN SET NOCOUNT ON; EXEC dbo.usp_MemberVisitorAiSnapshotInternal @UserKey=@UserKey,@OwnerPreview=1; END;';
DENY EXECUTE ON dbo.usp_MemberVisitorAiSnapshotInternal TO PUBLIC;
IF NOT EXISTS(SELECT 1 FROM dbo.schema_migrations WHERE migration_id=N'PS-VISITOR-AI-001')
    INSERT dbo.schema_migrations(migration_id,description,application_version)
    VALUES(N'PS-VISITOR-AI-001',N'Proposed read-only member visitor AI eligibility',N'PeerSlate MVP1 Package F');
COMMIT;
END TRY
BEGIN CATCH
IF XACT_STATE()<>0 ROLLBACK;
THROW;
END CATCH;
