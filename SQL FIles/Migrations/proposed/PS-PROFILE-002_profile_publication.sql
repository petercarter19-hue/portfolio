/* PS-PROFILE-002 — governed Profile publication, dark additive candidate.

   This migration is intentionally un-applied. It stores Profile-native draft
   versions and immutable audience publication manifests; exact canonical
   source references are normalized separately from the JSON compatibility
   envelope returned by the repository. It neither registers Profile routes
   nor publishes/backfills any member. Connections activation remains gated
   on PS-CONNECT-002 and is not enabled by these tables.
*/
SET NOCOUNT ON;
SET XACT_ABORT ON;

BEGIN TRY
  BEGIN TRANSACTION;

  IF OBJECT_ID(N'dbo.schema_migrations', N'U') IS NULL
     OR NOT EXISTS (SELECT 1 FROM dbo.schema_migrations WHERE migration_id=N'PS-PLAT-002')
     OR NOT EXISTS (SELECT 1 FROM dbo.schema_migrations WHERE migration_id=N'PS-PLAT-005')
     OR NOT EXISTS (SELECT 1 FROM dbo.schema_migrations WHERE migration_id=N'PS-AUTH-001')
    THROW 52900, 'PS-PROFILE-002 prerequisites are not applied.', 1;

  IF EXISTS (SELECT 1 FROM dbo.schema_migrations WHERE migration_id=N'PS-PROFILE-002')
  BEGIN
    IF OBJECT_ID(N'dbo.profile_publications', N'U') IS NULL
      THROW 52901, 'PS-PROFILE-002 ledger/object mismatch.', 1;
    COMMIT;
    RETURN;
  END;

  CREATE TABLE dbo.profile_publications
  (
    profile_publication_id bigint IDENTITY(1,1) NOT NULL CONSTRAINT PK_profile_publications PRIMARY KEY,
    publication_key nvarchar(128) NOT NULL,
    owner_profile_id bigint NOT NULL,
    audience nvarchar(20) NOT NULL,
    current_revision_number int NOT NULL CONSTRAINT DF_profile_publications_revision DEFAULT 0,
    current_revision_id bigint NULL,
    publication_state nvarchar(20) NOT NULL CONSTRAINT DF_profile_publications_state DEFAULT N'draft',
    updated_at_utc datetime2(7) NOT NULL CONSTRAINT DF_profile_publications_updated DEFAULT SYSUTCDATETIME(),
    row_version rowversion NOT NULL,
    CONSTRAINT UQ_profile_publications_key UNIQUE(publication_key),
    CONSTRAINT UQ_profile_publications_owner_audience UNIQUE(owner_profile_id,audience),
    CONSTRAINT UQ_profile_publications_id_owner_audience UNIQUE(profile_publication_id,owner_profile_id,audience),
    CONSTRAINT FK_profile_publications_owner FOREIGN KEY(owner_profile_id) REFERENCES dbo.member_profiles(profile_id),
    CONSTRAINT CK_profile_publications_audience CHECK(audience IN(N'public',N'connections')),
    CONSTRAINT CK_profile_publications_state CHECK(publication_state IN(N'draft',N'published',N'withdrawn')),
    CONSTRAINT CK_profile_publications_revision CHECK(current_revision_number>=0)
  );

  CREATE TABLE dbo.profile_content_items
  (
    profile_content_item_id bigint IDENTITY(1,1) NOT NULL CONSTRAINT PK_profile_content_items PRIMARY KEY,
    content_key nvarchar(128) NOT NULL,
    owner_profile_id bigint NOT NULL,
    content_kind nvarchar(40) NOT NULL,
    active bit NOT NULL CONSTRAINT DF_profile_content_items_active DEFAULT 1,
    created_at_utc datetime2(7) NOT NULL CONSTRAINT DF_profile_content_items_created DEFAULT SYSUTCDATETIME(),
    CONSTRAINT UQ_profile_content_items_key UNIQUE(content_key),
    CONSTRAINT UQ_profile_content_items_id_owner UNIQUE(profile_content_item_id,owner_profile_id),
    CONSTRAINT FK_profile_content_items_owner FOREIGN KEY(owner_profile_id) REFERENCES dbo.member_profiles(profile_id),
    CONSTRAINT CK_profile_content_items_kind CHECK(content_kind IN(N'identity',N'current_chapter',N'about',N'community_post_reference',N'project_reference',N'media_reference',N'voice_reference'))
  );

  CREATE TABLE dbo.profile_content_versions
  (
    profile_content_version_id bigint IDENTITY(1,1) NOT NULL CONSTRAINT PK_profile_content_versions PRIMARY KEY,
    profile_content_item_id bigint NOT NULL,
    owner_profile_id bigint NOT NULL,
    version_number int NOT NULL,
    body_json nvarchar(max) NOT NULL,
    body_sha256 char(64) NOT NULL,
    created_at_utc datetime2(7) NOT NULL CONSTRAINT DF_profile_content_versions_created DEFAULT SYSUTCDATETIME(),
    CONSTRAINT UQ_profile_content_versions_item_version UNIQUE(profile_content_item_id,version_number),
    CONSTRAINT UQ_profile_content_versions_id_owner UNIQUE(profile_content_version_id,owner_profile_id),
    CONSTRAINT FK_profile_content_versions_item_owner FOREIGN KEY(profile_content_item_id,owner_profile_id) REFERENCES dbo.profile_content_items(profile_content_item_id,owner_profile_id),
    CONSTRAINT CK_profile_content_versions_number CHECK(version_number>0),
    CONSTRAINT CK_profile_content_versions_json CHECK(ISJSON(body_json)=1),
    CONSTRAINT CK_profile_content_versions_digest CHECK(body_sha256 NOT LIKE '%[^0-9a-f]%')
  );

  CREATE TABLE dbo.profile_projection_versions
  (
    profile_projection_version_id bigint IDENTITY(1,1) NOT NULL CONSTRAINT PK_profile_projection_versions PRIMARY KEY,
    projection_key nvarchar(128) NOT NULL,
    owner_profile_id bigint NOT NULL,
    source_room nvarchar(30) NOT NULL,
    source_key nvarchar(128) NOT NULL,
    source_version nvarchar(128) NOT NULL,
    projection_version int NOT NULL,
    audience nvarchar(20) NOT NULL,
    approved_metadata_json nvarchar(max) NOT NULL,
    projection_sha256 char(64) NOT NULL,
    revoked_at_utc datetime2(7) NULL,
    created_at_utc datetime2(7) NOT NULL CONSTRAINT DF_profile_projection_versions_created DEFAULT SYSUTCDATETIME(),
    CONSTRAINT UQ_profile_projection_versions_key_version UNIQUE(projection_key,projection_version),
    CONSTRAINT UQ_profile_projection_versions_id_owner UNIQUE(profile_projection_version_id,owner_profile_id),
    CONSTRAINT FK_profile_projection_versions_owner FOREIGN KEY(owner_profile_id) REFERENCES dbo.member_profiles(profile_id),
    CONSTRAINT CK_profile_projection_versions_room CHECK(source_room IN(N'community',N'projects',N'media',N'voice')),
    CONSTRAINT CK_profile_projection_versions_audience CHECK(audience IN(N'public',N'connections')),
    CONSTRAINT CK_profile_projection_versions_number CHECK(projection_version>0),
    CONSTRAINT CK_profile_projection_versions_json CHECK(ISJSON(approved_metadata_json)=1),
    CONSTRAINT CK_profile_projection_versions_digest CHECK(projection_sha256 NOT LIKE '%[^0-9a-f]%')
  );

  CREATE TABLE dbo.profile_drafts
  (
    profile_draft_id bigint IDENTITY(1,1) NOT NULL CONSTRAINT PK_profile_drafts PRIMARY KEY,
    draft_key nvarchar(128) NOT NULL,
    owner_profile_id bigint NOT NULL,
    profile_slug nvarchar(64) NOT NULL,
    draft_version nvarchar(128) NOT NULL,
    manifest_json nvarchar(max) NOT NULL,
    manifest_sha256 char(64) NOT NULL,
    updated_at_utc datetime2(7) NOT NULL CONSTRAINT DF_profile_drafts_updated DEFAULT SYSUTCDATETIME(),
    row_version rowversion NOT NULL,
    CONSTRAINT UQ_profile_drafts_key UNIQUE(draft_key),
    CONSTRAINT UQ_profile_drafts_owner UNIQUE(owner_profile_id),
    CONSTRAINT UQ_profile_drafts_id_owner UNIQUE(profile_draft_id,owner_profile_id),
    CONSTRAINT FK_profile_drafts_owner FOREIGN KEY(owner_profile_id) REFERENCES dbo.member_profiles(profile_id),
    CONSTRAINT CK_profile_drafts_json CHECK(ISJSON(manifest_json)=1),
    CONSTRAINT CK_profile_drafts_digest CHECK(manifest_sha256 NOT LIKE '%[^0-9a-f]%')
  );

  CREATE TABLE dbo.profile_draft_placements
  (
    profile_draft_placement_id bigint IDENTITY(1,1) NOT NULL CONSTRAINT PK_profile_draft_placements PRIMARY KEY,
    placement_key nvarchar(128) NOT NULL,
    profile_draft_id bigint NOT NULL,
    owner_profile_id bigint NOT NULL,
    destination nvarchar(20) NOT NULL,
    region nvarchar(64) NOT NULL,
    rank int NOT NULL,
    featured bit NOT NULL,
    profile_content_version_id bigint NULL,
    profile_projection_version_id bigint NULL,
    CONSTRAINT UQ_profile_draft_placements_key UNIQUE(placement_key),
    CONSTRAINT UQ_profile_draft_placements_position UNIQUE(profile_draft_id,destination,region,rank),
    CONSTRAINT FK_profile_draft_placements_draft_owner FOREIGN KEY(profile_draft_id,owner_profile_id) REFERENCES dbo.profile_drafts(profile_draft_id,owner_profile_id) ON DELETE CASCADE,
    CONSTRAINT FK_profile_draft_placements_content_owner FOREIGN KEY(profile_content_version_id,owner_profile_id) REFERENCES dbo.profile_content_versions(profile_content_version_id,owner_profile_id),
    CONSTRAINT FK_profile_draft_placements_projection_owner FOREIGN KEY(profile_projection_version_id,owner_profile_id) REFERENCES dbo.profile_projection_versions(profile_projection_version_id,owner_profile_id),
    CONSTRAINT CK_profile_draft_placements_destination CHECK(destination IN(N'home',N'posts',N'projects',N'media',N'voice',N'about')),
    CONSTRAINT CK_profile_draft_placements_rank CHECK(rank BETWEEN 0 AND 100000),
    CONSTRAINT CK_profile_draft_placements_one_source CHECK((CASE WHEN profile_content_version_id IS NULL THEN 0 ELSE 1 END)+(CASE WHEN profile_projection_version_id IS NULL THEN 0 ELSE 1 END)=1)
  );

  CREATE TABLE dbo.profile_publication_revisions
  (
    profile_publication_revision_id bigint IDENTITY(1,1) NOT NULL CONSTRAINT PK_profile_publication_revisions PRIMARY KEY,
    revision_key nvarchar(128) NOT NULL,
    profile_publication_id bigint NOT NULL,
    owner_profile_id bigint NOT NULL,
    audience nvarchar(20) NOT NULL,
    revision_number int NOT NULL,
    profile_slug nvarchar(64) NOT NULL,
    manifest_json nvarchar(max) NOT NULL,
    manifest_sha256 char(64) NOT NULL,
    identity_content_version_id bigint NULL,
    chapter_content_version_id bigint NULL,
    about_content_version_id bigint NULL,
    created_at_utc datetime2(7) NOT NULL CONSTRAINT DF_profile_publication_revisions_created DEFAULT SYSUTCDATETIME(),
    CONSTRAINT UQ_profile_publication_revisions_key UNIQUE(revision_key),
    CONSTRAINT UQ_profile_publication_revisions_number UNIQUE(profile_publication_id,revision_number),
    CONSTRAINT UQ_profile_publication_revisions_id_owner UNIQUE(profile_publication_revision_id,owner_profile_id),
    CONSTRAINT UQ_profile_publication_revisions_id_owner_audience UNIQUE(profile_publication_revision_id,owner_profile_id,audience),
    CONSTRAINT FK_profile_publication_revisions_root_owner_audience FOREIGN KEY(profile_publication_id,owner_profile_id,audience) REFERENCES dbo.profile_publications(profile_publication_id,owner_profile_id,audience),
    CONSTRAINT FK_profile_publication_revisions_owner FOREIGN KEY(owner_profile_id) REFERENCES dbo.member_profiles(profile_id),
    CONSTRAINT FK_profile_publication_revisions_identity FOREIGN KEY(identity_content_version_id,owner_profile_id) REFERENCES dbo.profile_content_versions(profile_content_version_id,owner_profile_id),
    CONSTRAINT FK_profile_publication_revisions_chapter FOREIGN KEY(chapter_content_version_id,owner_profile_id) REFERENCES dbo.profile_content_versions(profile_content_version_id,owner_profile_id),
    CONSTRAINT FK_profile_publication_revisions_about FOREIGN KEY(about_content_version_id,owner_profile_id) REFERENCES dbo.profile_content_versions(profile_content_version_id,owner_profile_id),
    CONSTRAINT CK_profile_publication_revisions_audience CHECK(audience IN(N'public',N'connections')),
    CONSTRAINT CK_profile_publication_revisions_number CHECK(revision_number>0),
    CONSTRAINT CK_profile_publication_revisions_json CHECK(ISJSON(manifest_json)=1),
    CONSTRAINT CK_profile_publication_revisions_digest CHECK(manifest_sha256 NOT LIKE '%[^0-9a-f]%')
  );

  CREATE TABLE dbo.profile_publication_revision_items
  (
    profile_publication_revision_item_id bigint IDENTITY(1,1) NOT NULL CONSTRAINT PK_profile_publication_revision_items PRIMARY KEY,
    profile_publication_revision_id bigint NOT NULL,
    owner_profile_id bigint NOT NULL,
    placement_key nvarchar(128) NOT NULL,
    destination nvarchar(20) NOT NULL,
    region nvarchar(64) NOT NULL,
    rank int NOT NULL,
    featured bit NOT NULL,
    profile_content_version_id bigint NULL,
    profile_projection_version_id bigint NULL,
    CONSTRAINT UQ_profile_publication_revision_items_position UNIQUE(profile_publication_revision_id,destination,region,rank),
    CONSTRAINT FK_profile_publication_revision_items_revision_owner FOREIGN KEY(profile_publication_revision_id,owner_profile_id) REFERENCES dbo.profile_publication_revisions(profile_publication_revision_id,owner_profile_id),
    CONSTRAINT FK_profile_publication_revision_items_content_owner FOREIGN KEY(profile_content_version_id,owner_profile_id) REFERENCES dbo.profile_content_versions(profile_content_version_id,owner_profile_id),
    CONSTRAINT FK_profile_publication_revision_items_projection_owner FOREIGN KEY(profile_projection_version_id,owner_profile_id) REFERENCES dbo.profile_projection_versions(profile_projection_version_id,owner_profile_id),
    CONSTRAINT CK_profile_publication_revision_items_destination CHECK(destination IN(N'home',N'posts',N'projects',N'media',N'voice',N'about')),
    CONSTRAINT CK_profile_publication_revision_items_rank CHECK(rank BETWEEN 0 AND 100000),
    CONSTRAINT CK_profile_publication_revision_items_one_source CHECK((CASE WHEN profile_content_version_id IS NULL THEN 0 ELSE 1 END)+(CASE WHEN profile_projection_version_id IS NULL THEN 0 ELSE 1 END)=1)
  );

  CREATE TABLE dbo.profile_publication_commands
  (
    profile_publication_command_id bigint IDENTITY(1,1) NOT NULL CONSTRAINT PK_profile_publication_commands PRIMARY KEY,
    command_key nvarchar(128) NOT NULL,
    owner_profile_id bigint NOT NULL,
    idempotency_key nvarchar(128) NOT NULL,
    request_sha256 char(64) NOT NULL,
    profile_publication_revision_id bigint NOT NULL,
    created_at_utc datetime2(7) NOT NULL CONSTRAINT DF_profile_publication_commands_created DEFAULT SYSUTCDATETIME(),
    CONSTRAINT UQ_profile_publication_commands_key UNIQUE(command_key),
    CONSTRAINT UQ_profile_publication_commands_owner_request UNIQUE(owner_profile_id,idempotency_key),
    CONSTRAINT FK_profile_publication_commands_revision_owner FOREIGN KEY(profile_publication_revision_id,owner_profile_id) REFERENCES dbo.profile_publication_revisions(profile_publication_revision_id,owner_profile_id),
    CONSTRAINT CK_profile_publication_commands_digest CHECK(request_sha256 NOT LIKE '%[^0-9a-f]%')
  );

  CREATE TABLE dbo.profile_slug_history
  (
    profile_slug_history_id bigint IDENTITY(1,1) NOT NULL CONSTRAINT PK_profile_slug_history PRIMARY KEY,
    owner_profile_id bigint NOT NULL,
    normalized_slug nvarchar(64) NOT NULL,
    active bit NOT NULL,
    reserved_at_utc datetime2(7) NOT NULL CONSTRAINT DF_profile_slug_history_reserved DEFAULT SYSUTCDATETIME(),
    released_at_utc datetime2(7) NULL,
    CONSTRAINT UQ_profile_slug_history_slug UNIQUE(normalized_slug),
    CONSTRAINT FK_profile_slug_history_owner FOREIGN KEY(owner_profile_id) REFERENCES dbo.member_profiles(profile_id),
    CONSTRAINT CK_profile_slug_history_release CHECK((active=1 AND released_at_utc IS NULL) OR (active=0 AND released_at_utc IS NOT NULL))
  );

  /* Add the self-reference only after both tables exist. */
  ALTER TABLE dbo.profile_publications ADD CONSTRAINT FK_profile_publications_current_revision
    FOREIGN KEY(current_revision_id,owner_profile_id,audience) REFERENCES dbo.profile_publication_revisions(profile_publication_revision_id,owner_profile_id,audience);

  /* Procedures are created transactionally through dynamic DDL so the ledger
     can never claim a partial durable boundary. */
  EXEC sys.sp_executesql N'
  CREATE OR ALTER PROCEDURE dbo.usp_GetProfileOwnerBySlug @ProfileSlug nvarchar(64)
  AS
  BEGIN
    SET NOCOUNT ON;
    SELECT app_user.user_key AS owner_key
    FROM dbo.profile_slug_history AS slug
    JOIN dbo.member_profiles AS profile ON profile.profile_id=slug.owner_profile_id AND profile.active=1
    JOIN dbo.app_users AS app_user ON app_user.id=profile.user_id AND app_user.active=1
    WHERE slug.normalized_slug=LOWER(@ProfileSlug) AND slug.active=1;
  END';

  EXEC sys.sp_executesql N'
  CREATE OR ALTER PROCEDURE dbo.usp_GetProfileDraftForOwner @OwnerKey nvarchar(300)
  AS
  BEGIN
    SET NOCOUNT ON;
    SELECT draft.manifest_json
    FROM dbo.app_users AS app_user
    JOIN dbo.member_profiles AS profile ON profile.user_id=app_user.id AND profile.active=1
    JOIN dbo.profile_drafts AS draft ON draft.owner_profile_id=profile.profile_id
    WHERE app_user.user_key=@OwnerKey AND app_user.active=1;
  END';

  EXEC sys.sp_executesql N'
  CREATE OR ALTER PROCEDURE dbo.usp_GetCurrentProfilePublicationForOwner
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

  EXEC sys.sp_executesql N'
  CREATE OR ALTER PROCEDURE dbo.usp_GetProfilePublicationCommandForOwner
    @OwnerKey nvarchar(300), @IdempotencyKey nvarchar(128)
  AS
  BEGIN
    SET NOCOUNT ON;
    SELECT command.command_key, app_user.user_key AS owner_key,
           command.idempotency_key, command.request_sha256 AS request_digest,
           revision.manifest_json
    FROM dbo.app_users AS app_user
    JOIN dbo.member_profiles AS profile ON profile.user_id=app_user.id AND profile.active=1
    JOIN dbo.profile_publication_commands AS command ON command.owner_profile_id=profile.profile_id AND command.idempotency_key=@IdempotencyKey
    JOIN dbo.profile_publication_revisions AS revision ON revision.profile_publication_revision_id=command.profile_publication_revision_id AND revision.owner_profile_id=profile.profile_id
    WHERE app_user.user_key=@OwnerKey AND app_user.active=1;
  END';

  EXEC sys.sp_executesql N'
  CREATE OR ALTER PROCEDURE dbo.usp_SaveProfileDraftForOwner
    @OwnerKey nvarchar(300), @ProfileSlug nvarchar(64), @ExpectedDraftVersion nvarchar(128)=NULL,
    @DraftVersion nvarchar(128), @ManifestJson nvarchar(max)
  AS
  BEGIN
    SET NOCOUNT ON; SET XACT_ABORT ON;
    IF @OwnerKey IS NULL OR @ProfileSlug IS NULL OR @DraftVersion IS NULL OR @ManifestJson IS NULL
       OR ISJSON(@ManifestJson)<>1
       OR JSON_VALUE(@ManifestJson,''$.draft_key'') IS NULL
       OR JSON_VALUE(@ManifestJson,''$.owner_key'') IS NULL OR JSON_VALUE(@ManifestJson,''$.owner_key'') COLLATE Latin1_General_100_BIN2<>@OwnerKey COLLATE Latin1_General_100_BIN2
       OR JSON_VALUE(@ManifestJson,''$.slug'') IS NULL OR JSON_VALUE(@ManifestJson,''$.slug'') COLLATE Latin1_General_100_BIN2<>@ProfileSlug COLLATE Latin1_General_100_BIN2
       OR JSON_VALUE(@ManifestJson,''$.version'') IS NULL OR JSON_VALUE(@ManifestJson,''$.version'') COLLATE Latin1_General_100_BIN2<>@DraftVersion COLLATE Latin1_General_100_BIN2
      THROW 52910,''Invalid Profile draft manifest.'',1;
    DECLARE @OwnerProfileId bigint=(SELECT profile.profile_id FROM dbo.member_profiles profile JOIN dbo.app_users app_user ON app_user.id=profile.user_id WHERE app_user.user_key=@OwnerKey AND app_user.active=1 AND profile.active=1);
    IF @OwnerProfileId IS NULL THROW 52911,''Profile owner unavailable.'',1;
    BEGIN TRANSACTION;
    DECLARE @LockResult int;
    EXEC @LockResult=sys.sp_getapplock @Resource=CONCAT(N''profile-draft:'',@OwnerProfileId),@LockMode=N''Exclusive'',@LockOwner=N''Transaction'',@LockTimeout=5000;
    IF @LockResult<0 THROW 52917,''Profile draft lock unavailable.'',1;
    DECLARE @DraftId bigint,@CurrentDraftKey nvarchar(128),@CurrentDraftVersion nvarchar(128);
    SELECT @DraftId=profile_draft_id,@CurrentDraftKey=draft_key,@CurrentDraftVersion=draft_version FROM dbo.profile_drafts WITH(UPDLOCK,HOLDLOCK) WHERE owner_profile_id=@OwnerProfileId;
    IF (@ExpectedDraftVersion IS NULL AND @DraftId IS NOT NULL)
       OR (@ExpectedDraftVersion IS NOT NULL AND (@DraftId IS NULL OR @CurrentDraftVersion IS NULL OR @ExpectedDraftVersion COLLATE Latin1_General_100_BIN2<>@CurrentDraftVersion COLLATE Latin1_General_100_BIN2))
       OR (@DraftId IS NOT NULL AND (@CurrentDraftKey IS NULL OR @CurrentDraftKey COLLATE Latin1_General_100_BIN2<>JSON_VALUE(@ManifestJson,''$.draft_key'') COLLATE Latin1_General_100_BIN2))
    BEGIN COMMIT; SELECT CAST(0 AS bit) saved; RETURN; END;
    IF EXISTS(SELECT 1 FROM dbo.profile_slug_history WITH(UPDLOCK,HOLDLOCK) WHERE normalized_slug=@ProfileSlug AND owner_profile_id<>@OwnerProfileId)
      THROW 52912,''Profile slug unavailable.'',1;
    IF NOT EXISTS(SELECT 1 FROM dbo.profile_slug_history WHERE normalized_slug=@ProfileSlug)
      INSERT dbo.profile_slug_history(owner_profile_id,normalized_slug,active) VALUES(@OwnerProfileId,@ProfileSlug,1);
    IF @DraftId IS NULL
    BEGIN
      INSERT dbo.profile_drafts(draft_key,owner_profile_id,profile_slug,draft_version,manifest_json,manifest_sha256)
      VALUES(JSON_VALUE(@ManifestJson,''$.draft_key''),@OwnerProfileId,@ProfileSlug,@DraftVersion,@ManifestJson,CONVERT(varchar(64),HASHBYTES(''SHA2_256'',CONVERT(varbinary(max),@ManifestJson)),2));
      SET @DraftId=SCOPE_IDENTITY();
    END
    ELSE UPDATE dbo.profile_drafts SET profile_slug=@ProfileSlug,draft_version=@DraftVersion,manifest_json=@ManifestJson,manifest_sha256=CONVERT(varchar(64),HASHBYTES(''SHA2_256'',CONVERT(varbinary(max),@ManifestJson)),2),updated_at_utc=SYSUTCDATETIME() WHERE profile_draft_id=@DraftId;
    DELETE dbo.profile_draft_placements WHERE profile_draft_id=@DraftId;
    DECLARE @Kind nvarchar(40), @Body nvarchar(max);
    DECLARE native_cursor CURSOR LOCAL FAST_FORWARD FOR
      SELECT kind,body FROM (VALUES(N''identity'',JSON_QUERY(@ManifestJson,''$.identity'')),(N''current_chapter'',JSON_QUERY(@ManifestJson,''$.current_chapter'')),(N''about'',JSON_QUERY(@ManifestJson,''$.about''))) native(kind,body) WHERE body IS NOT NULL;
    OPEN native_cursor; FETCH NEXT FROM native_cursor INTO @Kind,@Body;
    WHILE @@FETCH_STATUS=0
    BEGIN
      DECLARE @ItemId bigint=(SELECT TOP(1) profile_content_item_id FROM dbo.profile_content_items WHERE owner_profile_id=@OwnerProfileId AND content_kind=@Kind AND active=1 ORDER BY profile_content_item_id);
      IF @ItemId IS NULL BEGIN INSERT dbo.profile_content_items(content_key,owner_profile_id,content_kind) VALUES(CONCAT(N''native_'',@Kind,N''_'',CONVERT(nvarchar(36),NEWID())),@OwnerProfileId,@Kind); SET @ItemId=SCOPE_IDENTITY(); END;
      INSERT dbo.profile_content_versions(profile_content_item_id,owner_profile_id,version_number,body_json,body_sha256)
      SELECT @ItemId,@OwnerProfileId,ISNULL(MAX(version_number),0)+1,@Body,CONVERT(varchar(64),HASHBYTES(''SHA2_256'',CONVERT(varbinary(max),@Body)),2) FROM dbo.profile_content_versions WITH(UPDLOCK,HOLDLOCK) WHERE profile_content_item_id=@ItemId;
      FETCH NEXT FROM native_cursor INTO @Kind,@Body;
    END
    CLOSE native_cursor; DEALLOCATE native_cursor;
    INSERT dbo.profile_projection_versions(projection_key,owner_profile_id,source_room,source_key,source_version,projection_version,audience,approved_metadata_json,projection_sha256)
    SELECT p.placement_key,@OwnerProfileId,N''community'',p.source_key,p.source_version,
           ISNULL((SELECT MAX(existing.projection_version) FROM dbo.profile_projection_versions existing WITH(UPDLOCK,HOLDLOCK) WHERE existing.projection_key=p.placement_key),0)+1,
           N''public'',p.metadata_json,CONVERT(varchar(64),HASHBYTES(''SHA2_256'',CONVERT(varbinary(max),p.metadata_json)),2)
    FROM OPENJSON(@ManifestJson,''$.placements'') WITH(placement_key nvarchar(128) ''$.placement_key'',content_kind nvarchar(40) ''$.content_kind'',source_key nvarchar(128) ''$.source_reference.source_key'',source_version nvarchar(128) ''$.source_reference.source_revision'',metadata_json nvarchar(max) ''$.source_reference'' AS JSON) p
    WHERE p.content_kind=N''community_post_reference'' AND p.source_key IS NOT NULL
      AND NOT EXISTS
      (
        SELECT 1 FROM dbo.profile_projection_versions existing
        WHERE existing.projection_key=p.placement_key AND existing.owner_profile_id=@OwnerProfileId
          AND existing.source_key=p.source_key AND existing.source_version=p.source_version
          AND existing.audience=N''public'' AND existing.approved_metadata_json=p.metadata_json
          AND existing.revoked_at_utc IS NULL
      );
    INSERT dbo.profile_draft_placements(placement_key,profile_draft_id,owner_profile_id,destination,region,rank,featured,profile_projection_version_id)
    SELECT p.placement_key,@DraftId,@OwnerProfileId,p.destination,p.region,p.rank,p.featured,projection.profile_projection_version_id
    FROM OPENJSON(@ManifestJson,''$.placements'') WITH
    (
      placement_key nvarchar(128) ''$.placement_key'',destination nvarchar(20) ''$.destination'',region nvarchar(64) ''$.region'',rank int ''$.rank'',featured bit ''$.featured'',
      source_key nvarchar(128) ''$.source_reference.source_key'',source_version nvarchar(128) ''$.source_reference.source_revision'',source_metadata nvarchar(max) ''$.source_reference'' AS JSON
    ) p
    CROSS APPLY
    (
      SELECT TOP(1) candidate.profile_projection_version_id
      FROM dbo.profile_projection_versions candidate
      WHERE candidate.projection_key=p.placement_key AND candidate.owner_profile_id=@OwnerProfileId
        AND candidate.source_key=p.source_key AND candidate.source_version=p.source_version
        AND candidate.audience=N''public'' AND candidate.approved_metadata_json=p.source_metadata
        AND candidate.revoked_at_utc IS NULL
      ORDER BY candidate.projection_version DESC
    ) projection;
    IF (SELECT COUNT_BIG(*) FROM dbo.profile_draft_placements WHERE profile_draft_id=@DraftId)
       <>(SELECT COUNT_BIG(*) FROM OPENJSON(@ManifestJson,''$.placements''))
      THROW 52916,''Profile draft placement persistence mismatch.'',1;
    COMMIT;
    SELECT CAST(1 AS bit) AS saved;
  END';

  EXEC sys.sp_executesql N'
  CREATE OR ALTER PROCEDURE dbo.usp_CommitProfilePublicationForOwner
    @OwnerKey nvarchar(300), @Audience nvarchar(20), @PublicationAction nvarchar(20), @ExpectedPublicRevision nvarchar(128)=NULL,
    @ExpectedDraftKey nvarchar(128), @ExpectedDraftVersion nvarchar(128),
    @ExpectedDraftManifestJson nvarchar(max),
    @RevisionKey nvarchar(128), @RevisionNumber int,
    @RevisionDigest char(64), @ManifestJson nvarchar(max), @CommandKey nvarchar(128),
    @IdempotencyKey nvarchar(128), @RequestDigest char(64)
  AS
  BEGIN
    SET NOCOUNT ON; SET XACT_ABORT ON;
    IF @OwnerKey IS NULL OR @Audience IS NULL OR @PublicationAction IS NULL OR @RevisionKey IS NULL OR @RevisionNumber IS NULL OR @RevisionDigest IS NULL OR @ManifestJson IS NULL OR @CommandKey IS NULL OR @IdempotencyKey IS NULL OR @RequestDigest IS NULL
       OR @Audience COLLATE Latin1_General_100_BIN2 NOT IN(N''public'',N''connections'')
       OR @PublicationAction COLLATE Latin1_General_100_BIN2 NOT IN(N''publish'',N''withdraw'') OR ISJSON(@ManifestJson)<>1
       OR JSON_VALUE(@ManifestJson,''$.owner_key'') IS NULL OR JSON_VALUE(@ManifestJson,''$.owner_key'') COLLATE Latin1_General_100_BIN2<>@OwnerKey COLLATE Latin1_General_100_BIN2
       OR JSON_VALUE(@ManifestJson,''$.audience'') IS NULL OR JSON_VALUE(@ManifestJson,''$.audience'') COLLATE Latin1_General_100_BIN2<>@Audience COLLATE Latin1_General_100_BIN2
       OR JSON_VALUE(@ManifestJson,''$.action'') IS NULL OR JSON_VALUE(@ManifestJson,''$.action'') COLLATE Latin1_General_100_BIN2<>@PublicationAction COLLATE Latin1_General_100_BIN2
       OR JSON_VALUE(@ManifestJson,''$.revision_key'') IS NULL OR JSON_VALUE(@ManifestJson,''$.revision_key'') COLLATE Latin1_General_100_BIN2<>@RevisionKey COLLATE Latin1_General_100_BIN2
       OR JSON_VALUE(@ManifestJson,''$.digest'') IS NULL OR JSON_VALUE(@ManifestJson,''$.digest'') COLLATE Latin1_General_100_BIN2<>@RevisionDigest COLLATE Latin1_General_100_BIN2
       OR JSON_VALUE(@ManifestJson,''$.revision_number'') IS NULL OR TRY_CONVERT(int,JSON_VALUE(@ManifestJson,''$.revision_number''))<>@RevisionNumber
       OR EXISTS(SELECT 1 FROM OPENJSON(@ManifestJson) root WHERE root.[key] COLLATE Latin1_General_100_BIN2 NOT IN(N''revision_key'',N''owner_key'',N''slug'',N''audience'',N''action'',N''revision_number'',N''created_at'',N''digest'',N''identity'',N''current_chapter'',N''about'',N''items''))
       OR EXISTS
       (
         SELECT 1
         FROM (VALUES(N''revision_key''),(N''owner_key''),(N''slug''),(N''audience''),(N''action''),(N''revision_number''),(N''created_at''),(N''digest''),(N''identity''),(N''current_chapter''),(N''about''),(N''items'')) required(root_key)
         OUTER APPLY(SELECT COUNT_BIG(*) found_count FROM OPENJSON(@ManifestJson) manifest WHERE manifest.[key] COLLATE Latin1_General_100_BIN2=required.root_key COLLATE Latin1_General_100_BIN2) found
         WHERE found.found_count<>1
       )
      THROW 52913,''Invalid Profile publication manifest.'',1;
    DECLARE @OwnerProfileId bigint=(SELECT profile.profile_id FROM dbo.member_profiles profile JOIN dbo.app_users app_user ON app_user.id=profile.user_id WHERE app_user.user_key=@OwnerKey AND app_user.active=1 AND profile.active=1);
    IF @OwnerProfileId IS NULL THROW 52914,''Profile owner unavailable.'',1;
    BEGIN TRANSACTION;
    DECLARE @LockResult int;
    EXEC @LockResult=sys.sp_getapplock @Resource=CONCAT(N''profile-publish:'',@OwnerProfileId,N'':'',@Audience),@LockMode=N''Exclusive'',@LockOwner=N''Transaction'',@LockTimeout=5000;
    IF @LockResult<0 THROW 52918,''Profile publication lock unavailable.'',1;
    DECLARE @ExistingDigest char(64)=(SELECT request_sha256 FROM dbo.profile_publication_commands WITH(UPDLOCK,HOLDLOCK) WHERE owner_profile_id=@OwnerProfileId AND idempotency_key=@IdempotencyKey);
    IF @ExistingDigest IS NOT NULL
    BEGIN
      IF @RequestDigest IS NULL OR @ExistingDigest COLLATE Latin1_General_100_BIN2<>@RequestDigest COLLATE Latin1_General_100_BIN2 THROW 52915,''Profile idempotency conflict.'',1;
      COMMIT;
      SELECT CAST(1 AS bit) AS committed, command.command_key, app_user.user_key owner_key,
             command.idempotency_key, command.request_sha256 request_digest, revision.manifest_json
      FROM dbo.profile_publication_commands command
      JOIN dbo.profile_publication_revisions revision ON revision.profile_publication_revision_id=command.profile_publication_revision_id AND revision.owner_profile_id=command.owner_profile_id
      JOIN dbo.member_profiles profile ON profile.profile_id=command.owner_profile_id
      JOIN dbo.app_users app_user ON app_user.id=profile.user_id
      WHERE command.owner_profile_id=@OwnerProfileId AND command.idempotency_key=@IdempotencyKey;
      RETURN;
    END;
    DECLARE @DraftId bigint,@CurrentDraftKey nvarchar(128),@CurrentDraftVersion nvarchar(128),@CurrentDraftManifest nvarchar(max),@CurrentDraftDigest char(64);
    SELECT @DraftId=profile_draft_id,@CurrentDraftKey=draft_key,@CurrentDraftVersion=draft_version,@CurrentDraftManifest=manifest_json,@CurrentDraftDigest=manifest_sha256
    FROM dbo.profile_drafts WITH(UPDLOCK,HOLDLOCK) WHERE owner_profile_id=@OwnerProfileId;
    IF @DraftId IS NULL OR @ExpectedDraftKey IS NULL OR @ExpectedDraftVersion IS NULL OR @ExpectedDraftManifestJson IS NULL
       OR @CurrentDraftKey COLLATE Latin1_General_100_BIN2<>@ExpectedDraftKey COLLATE Latin1_General_100_BIN2 OR @CurrentDraftVersion COLLATE Latin1_General_100_BIN2<>@ExpectedDraftVersion COLLATE Latin1_General_100_BIN2
       OR @CurrentDraftManifest COLLATE Latin1_General_100_BIN2<>@ExpectedDraftManifestJson COLLATE Latin1_General_100_BIN2
       OR @CurrentDraftDigest COLLATE Latin1_General_100_BIN2<>CONVERT(varchar(64),HASHBYTES(''SHA2_256'',CONVERT(varbinary(max),@ExpectedDraftManifestJson)),2) COLLATE Latin1_General_100_BIN2
    BEGIN COMMIT; SELECT CAST(0 AS bit) committed; RETURN; END;
    IF JSON_VALUE(@ExpectedDraftManifestJson,''$.owner_key'') IS NULL OR JSON_VALUE(@ExpectedDraftManifestJson,''$.owner_key'') COLLATE Latin1_General_100_BIN2<>@OwnerKey COLLATE Latin1_General_100_BIN2
       OR JSON_VALUE(@ExpectedDraftManifestJson,''$.draft_key'') IS NULL OR JSON_VALUE(@ExpectedDraftManifestJson,''$.draft_key'') COLLATE Latin1_General_100_BIN2<>@ExpectedDraftKey COLLATE Latin1_General_100_BIN2
       OR JSON_VALUE(@ExpectedDraftManifestJson,''$.version'') IS NULL OR JSON_VALUE(@ExpectedDraftManifestJson,''$.version'') COLLATE Latin1_General_100_BIN2<>@ExpectedDraftVersion COLLATE Latin1_General_100_BIN2
       OR JSON_VALUE(@ExpectedDraftManifestJson,''$.slug'') IS NULL OR JSON_VALUE(@ManifestJson,''$.slug'') IS NULL
       OR JSON_VALUE(@ExpectedDraftManifestJson,''$.slug'') COLLATE Latin1_General_100_BIN2<>JSON_VALUE(@ManifestJson,''$.slug'') COLLATE Latin1_General_100_BIN2
    BEGIN COMMIT; SELECT CAST(0 AS bit) committed; RETURN; END;
    DECLARE @PublicationId bigint=(SELECT profile_publication_id FROM dbo.profile_publications WITH(UPDLOCK,HOLDLOCK) WHERE owner_profile_id=@OwnerProfileId AND audience COLLATE Latin1_General_100_BIN2=@Audience COLLATE Latin1_General_100_BIN2);
    DECLARE @CurrentRevisionKey nvarchar(128)=
    (
      SELECT revision.revision_key
      FROM dbo.profile_publications publication
      LEFT JOIN dbo.profile_publication_revisions revision ON revision.profile_publication_revision_id=publication.current_revision_id
      WHERE publication.owner_profile_id=@OwnerProfileId AND publication.audience COLLATE Latin1_General_100_BIN2=@Audience COLLATE Latin1_General_100_BIN2
    );
    IF (@ExpectedPublicRevision IS NULL AND @CurrentRevisionKey IS NOT NULL)
       OR (@ExpectedPublicRevision IS NOT NULL AND (@CurrentRevisionKey IS NULL OR @ExpectedPublicRevision COLLATE Latin1_General_100_BIN2<>@CurrentRevisionKey COLLATE Latin1_General_100_BIN2))
    BEGIN COMMIT; SELECT CAST(0 AS bit) committed; RETURN; END;
    DECLARE @CurrentRevisionNumber int=(SELECT current_revision_number FROM dbo.profile_publications WHERE profile_publication_id=@PublicationId);
    IF ISNULL(@CurrentRevisionNumber,0)+1<>@RevisionNumber BEGIN COMMIT; SELECT CAST(0 AS bit) committed; RETURN; END;
    DECLARE @ManifestItemCount bigint=(SELECT COUNT_BIG(*) FROM OPENJSON(@ManifestJson,''$.items''));
    DECLARE @DraftPlacementCount bigint=(SELECT COUNT_BIG(*) FROM dbo.profile_draft_placements WHERE profile_draft_id=@DraftId AND owner_profile_id=@OwnerProfileId);
    IF @PublicationAction=N''withdraw'' AND
    (
      EXISTS
      (
        SELECT 1
        FROM (VALUES(N''identity''),(N''current_chapter''),(N''about'')) expected(native_key)
        LEFT JOIN OPENJSON(@ManifestJson) native ON native.[key] COLLATE Latin1_General_100_BIN2=expected.native_key COLLATE Latin1_General_100_BIN2
        WHERE native.[key] IS NULL OR native.[type]<>0
      )
      OR NOT EXISTS(SELECT 1 FROM OPENJSON(@ManifestJson) root WHERE root.[key] COLLATE Latin1_General_100_BIN2=N''items'' COLLATE Latin1_General_100_BIN2 AND root.[type]=4)
      OR @ManifestItemCount<>0
      OR EXISTS(SELECT 1 FROM OPENJSON(@ManifestJson) root WHERE root.[key] COLLATE Latin1_General_100_BIN2=N''placements'' COLLATE Latin1_General_100_BIN2)
    ) BEGIN COMMIT; SELECT CAST(0 AS bit) committed; RETURN; END;
    IF @PublicationAction=N''publish'' AND
    (
      NOT EXISTS(SELECT 1 FROM OPENJSON(@ExpectedDraftManifestJson) native WHERE native.[key] COLLATE Latin1_General_100_BIN2=N''identity'' COLLATE Latin1_General_100_BIN2 AND native.[type]=5)
      OR NOT EXISTS(SELECT 1 FROM OPENJSON(@ManifestJson) root WHERE root.[key] COLLATE Latin1_General_100_BIN2=N''items'' COLLATE Latin1_General_100_BIN2 AND root.[type]=4)
      OR NOT EXISTS(SELECT 1 FROM OPENJSON(@ExpectedDraftManifestJson) root WHERE root.[key] COLLATE Latin1_General_100_BIN2=N''placements'' COLLATE Latin1_General_100_BIN2 AND root.[type]=4)
      OR EXISTS
      (
        SELECT 1
        FROM
        (
          SELECT [key], value, [type]
          FROM OPENJSON(@ManifestJson)
          WHERE [key] COLLATE Latin1_General_100_BIN2 IN(N''identity'',N''current_chapter'',N''about'')
        ) candidate_native
        FULL JOIN
        (
          SELECT [key], value, [type]
          FROM OPENJSON(@ExpectedDraftManifestJson)
          WHERE [key] COLLATE Latin1_General_100_BIN2 IN(N''identity'',N''current_chapter'',N''about'')
        ) draft_native ON draft_native.[key] COLLATE Latin1_General_100_BIN2=candidate_native.[key] COLLATE Latin1_General_100_BIN2
        WHERE candidate_native.[key] IS NULL OR draft_native.[key] IS NULL
           OR candidate_native.[type]<>draft_native.[type]
           OR (candidate_native.value IS NULL AND draft_native.value IS NOT NULL)
           OR (candidate_native.value IS NOT NULL AND draft_native.value IS NULL)
           OR (candidate_native.value IS NOT NULL AND draft_native.value IS NOT NULL AND candidate_native.value COLLATE Latin1_General_100_BIN2<>draft_native.value COLLATE Latin1_General_100_BIN2)
      )
      OR @ManifestItemCount<>@DraftPlacementCount
      OR @ManifestItemCount<>(SELECT COUNT_BIG(*) FROM OPENJSON(@ExpectedDraftManifestJson,''$.placements''))
      OR EXISTS
      (
        SELECT 1
        FROM OPENJSON(@ManifestJson,''$.items'') WITH
        (
          placement_key nvarchar(128) ''$.placement_key'',content_kind nvarchar(40) ''$.content_kind'',
          destination nvarchar(20) ''$.destination'',region nvarchar(64) ''$.region'',rank int ''$.rank'',featured bit ''$.featured'',
          source_key nvarchar(128) ''$.source_reference.source_key'',source_version nvarchar(128) ''$.source_reference.source_revision'',
          source_metadata nvarchar(max) ''$.source_reference'' AS JSON
        ) item
        FULL JOIN OPENJSON(@ExpectedDraftManifestJson,''$.placements'') WITH
        (
          placement_key nvarchar(128) ''$.placement_key'',content_kind nvarchar(40) ''$.content_kind'',
          destination nvarchar(20) ''$.destination'',region nvarchar(64) ''$.region'',rank int ''$.rank'',featured bit ''$.featured'',
          source_key nvarchar(128) ''$.source_reference.source_key'',source_version nvarchar(128) ''$.source_reference.source_revision'',
          source_metadata nvarchar(max) ''$.source_reference'' AS JSON
        ) draft_item ON draft_item.placement_key COLLATE Latin1_General_100_BIN2=item.placement_key COLLATE Latin1_General_100_BIN2
        WHERE item.placement_key IS NULL OR draft_item.placement_key IS NULL
           OR (item.content_kind IS NULL AND draft_item.content_kind IS NOT NULL)
           OR (item.content_kind IS NOT NULL AND draft_item.content_kind IS NULL)
           OR (item.content_kind IS NOT NULL AND draft_item.content_kind IS NOT NULL AND item.content_kind COLLATE Latin1_General_100_BIN2<>draft_item.content_kind COLLATE Latin1_General_100_BIN2)
           OR (item.destination IS NULL AND draft_item.destination IS NOT NULL)
           OR (item.destination IS NOT NULL AND draft_item.destination IS NULL)
           OR (item.destination IS NOT NULL AND draft_item.destination IS NOT NULL AND item.destination COLLATE Latin1_General_100_BIN2<>draft_item.destination COLLATE Latin1_General_100_BIN2)
           OR (item.region IS NULL AND draft_item.region IS NOT NULL)
           OR (item.region IS NOT NULL AND draft_item.region IS NULL)
           OR (item.region IS NOT NULL AND draft_item.region IS NOT NULL AND item.region COLLATE Latin1_General_100_BIN2<>draft_item.region COLLATE Latin1_General_100_BIN2)
           OR (item.rank IS NULL AND draft_item.rank IS NOT NULL)
           OR (item.rank IS NOT NULL AND draft_item.rank IS NULL)
           OR (item.rank IS NOT NULL AND draft_item.rank IS NOT NULL AND item.rank<>draft_item.rank)
           OR (item.featured IS NULL AND draft_item.featured IS NOT NULL)
           OR (item.featured IS NOT NULL AND draft_item.featured IS NULL)
           OR (item.featured IS NOT NULL AND draft_item.featured IS NOT NULL AND item.featured<>draft_item.featured)
           OR (item.source_key IS NULL AND draft_item.source_key IS NOT NULL)
           OR (item.source_key IS NOT NULL AND draft_item.source_key IS NULL)
           OR (item.source_key IS NOT NULL AND draft_item.source_key IS NOT NULL AND item.source_key COLLATE Latin1_General_100_BIN2<>draft_item.source_key COLLATE Latin1_General_100_BIN2)
           OR (item.source_version IS NULL AND draft_item.source_version IS NOT NULL)
           OR (item.source_version IS NOT NULL AND draft_item.source_version IS NULL)
           OR (item.source_version IS NOT NULL AND draft_item.source_version IS NOT NULL AND item.source_version COLLATE Latin1_General_100_BIN2<>draft_item.source_version COLLATE Latin1_General_100_BIN2)
           OR (item.source_metadata IS NULL AND draft_item.source_metadata IS NOT NULL)
           OR (item.source_metadata IS NOT NULL AND draft_item.source_metadata IS NULL)
           OR (item.source_metadata IS NOT NULL AND draft_item.source_metadata IS NOT NULL AND item.source_metadata COLLATE Latin1_General_100_BIN2<>draft_item.source_metadata COLLATE Latin1_General_100_BIN2)
      )
    ) BEGIN COMMIT; SELECT CAST(0 AS bit) committed; RETURN; END;
    IF @PublicationAction=N''publish'' AND @ManifestItemCount<>(SELECT COUNT_BIG(*) FROM OPENJSON(@ManifestJson,''$.items'') item JOIN dbo.profile_draft_placements placement ON placement.profile_draft_id=@DraftId AND placement.owner_profile_id=@OwnerProfileId AND placement.placement_key COLLATE Latin1_General_100_BIN2=JSON_VALUE(item.value,''$.placement_key'') COLLATE Latin1_General_100_BIN2)
    BEGIN COMMIT; SELECT CAST(0 AS bit) committed; RETURN; END;
    IF @PublicationAction=N''publish'' AND EXISTS
    (
      SELECT 1
      FROM OPENJSON(@ManifestJson,''$.items'') WITH
      (
        placement_key nvarchar(128) ''$.placement_key'',
        source_key nvarchar(128) ''$.source_reference.source_key'',
        source_version nvarchar(128) ''$.source_reference.source_revision'',
        source_metadata nvarchar(max) ''$.source_reference'' AS JSON
      ) item
      JOIN dbo.profile_draft_placements placement ON placement.profile_draft_id=@DraftId AND placement.owner_profile_id=@OwnerProfileId AND placement.placement_key COLLATE Latin1_General_100_BIN2=item.placement_key COLLATE Latin1_General_100_BIN2
      JOIN dbo.profile_projection_versions projection WITH(UPDLOCK,HOLDLOCK) ON projection.owner_profile_id=@OwnerProfileId AND projection.profile_projection_version_id=placement.profile_projection_version_id AND projection.source_room=N''community''
      WHERE projection.revoked_at_utc IS NOT NULL
         OR projection.audience COLLATE Latin1_General_100_BIN2<>@Audience COLLATE Latin1_General_100_BIN2
         OR item.source_key IS NULL OR projection.source_key COLLATE Latin1_General_100_BIN2<>item.source_key COLLATE Latin1_General_100_BIN2
         OR item.source_version IS NULL OR projection.source_version COLLATE Latin1_General_100_BIN2<>item.source_version COLLATE Latin1_General_100_BIN2
         OR item.source_metadata IS NULL OR projection.approved_metadata_json COLLATE Latin1_General_100_BIN2<>item.source_metadata COLLATE Latin1_General_100_BIN2
         OR NOT EXISTS
      (
        SELECT 1 FROM dbo.community_posts post WITH(UPDLOCK,HOLDLOCK) JOIN dbo.app_users author ON author.id=post.author_user_id
        WHERE author.user_key COLLATE Latin1_General_100_BIN2=@OwnerKey COLLATE Latin1_General_100_BIN2 AND CONVERT(nvarchar(128),post.post_key) COLLATE Latin1_General_100_BIN2=projection.source_key COLLATE Latin1_General_100_BIN2
          AND CONCAT(N''community:v'',post.revision_number) COLLATE Latin1_General_100_BIN2=projection.source_version COLLATE Latin1_General_100_BIN2
          AND post.publication_state=N''published'' AND post.moderation_state=N''clear'' AND post.audience=N''public''
      )
    ) THROW 52919,''Profile source reference is no longer eligible.'',1;
    DECLARE @IdentityVersionId bigint=NULL,@ChapterVersionId bigint=NULL,@AboutVersionId bigint=NULL;
    IF @PublicationAction=N''publish''
    BEGIN
      SELECT TOP(1) @IdentityVersionId=version.profile_content_version_id FROM dbo.profile_content_versions version JOIN dbo.profile_content_items item ON item.profile_content_item_id=version.profile_content_item_id WHERE item.owner_profile_id=@OwnerProfileId AND item.content_kind=N''identity'' ORDER BY version.version_number DESC;
      SELECT TOP(1) @ChapterVersionId=version.profile_content_version_id FROM dbo.profile_content_versions version JOIN dbo.profile_content_items item ON item.profile_content_item_id=version.profile_content_item_id WHERE item.owner_profile_id=@OwnerProfileId AND item.content_kind=N''current_chapter'' AND JSON_QUERY(@ManifestJson,''$.current_chapter'') IS NOT NULL ORDER BY version.version_number DESC;
      SELECT TOP(1) @AboutVersionId=version.profile_content_version_id FROM dbo.profile_content_versions version JOIN dbo.profile_content_items item ON item.profile_content_item_id=version.profile_content_item_id WHERE item.owner_profile_id=@OwnerProfileId AND item.content_kind=N''about'' AND JSON_QUERY(@ManifestJson,''$.about'') IS NOT NULL ORDER BY version.version_number DESC;
      IF @IdentityVersionId IS NULL OR (SELECT body_json FROM dbo.profile_content_versions WHERE profile_content_version_id=@IdentityVersionId) COLLATE Latin1_General_100_BIN2<>JSON_QUERY(@ManifestJson,''$.identity'') COLLATE Latin1_General_100_BIN2
         OR (JSON_QUERY(@ManifestJson,''$.current_chapter'') IS NOT NULL AND (@ChapterVersionId IS NULL OR (SELECT body_json FROM dbo.profile_content_versions WHERE profile_content_version_id=@ChapterVersionId) COLLATE Latin1_General_100_BIN2<>JSON_QUERY(@ManifestJson,''$.current_chapter'') COLLATE Latin1_General_100_BIN2))
         OR (JSON_QUERY(@ManifestJson,''$.about'') IS NOT NULL AND (@AboutVersionId IS NULL OR (SELECT body_json FROM dbo.profile_content_versions WHERE profile_content_version_id=@AboutVersionId) COLLATE Latin1_General_100_BIN2<>JSON_QUERY(@ManifestJson,''$.about'') COLLATE Latin1_General_100_BIN2))
      BEGIN COMMIT; SELECT CAST(0 AS bit) committed; RETURN; END;
    END;
    IF @PublicationId IS NULL
    BEGIN
      INSERT dbo.profile_publications(publication_key,owner_profile_id,audience)
      VALUES(CONCAT(N''publication_'',CONVERT(nvarchar(36),NEWID())),@OwnerProfileId,@Audience);
      SET @PublicationId=SCOPE_IDENTITY();
    END;
    INSERT dbo.profile_publication_revisions(revision_key,profile_publication_id,owner_profile_id,audience,revision_number,profile_slug,manifest_json,manifest_sha256,identity_content_version_id,chapter_content_version_id,about_content_version_id)
    VALUES(@RevisionKey,@PublicationId,@OwnerProfileId,@Audience,@RevisionNumber,JSON_VALUE(@ManifestJson,''$.slug''),@ManifestJson,@RevisionDigest,@IdentityVersionId,@ChapterVersionId,@AboutVersionId);
    DECLARE @RevisionId bigint=SCOPE_IDENTITY();
    INSERT dbo.profile_publication_revision_items(profile_publication_revision_id,owner_profile_id,placement_key,destination,region,rank,featured,profile_projection_version_id)
    SELECT @RevisionId,@OwnerProfileId,draft_placement.placement_key,draft_placement.destination,draft_placement.region,draft_placement.rank,draft_placement.featured,draft_placement.profile_projection_version_id
    FROM OPENJSON(@ManifestJson,''$.items'') WITH(placement_key nvarchar(128) ''$.placement_key'') item
    JOIN dbo.profile_draft_placements draft_placement ON draft_placement.profile_draft_id=@DraftId AND draft_placement.owner_profile_id=@OwnerProfileId AND draft_placement.placement_key COLLATE Latin1_General_100_BIN2=item.placement_key COLLATE Latin1_General_100_BIN2;
    UPDATE dbo.profile_publications SET current_revision_number=@RevisionNumber,current_revision_id=@RevisionId,publication_state=CASE WHEN @PublicationAction=N''withdraw'' THEN N''withdrawn'' ELSE N''published'' END,updated_at_utc=SYSUTCDATETIME() WHERE profile_publication_id=@PublicationId;
    INSERT dbo.profile_publication_commands(command_key,owner_profile_id,idempotency_key,request_sha256,profile_publication_revision_id) VALUES(@CommandKey,@OwnerProfileId,@IdempotencyKey,@RequestDigest,@RevisionId);
    COMMIT;
    SELECT CAST(1 AS bit) AS committed, @CommandKey command_key, @OwnerKey owner_key,
           @IdempotencyKey idempotency_key, @RequestDigest request_digest, @ManifestJson manifest_json;
  END';

  EXEC sys.sp_executesql N'
  CREATE OR ALTER PROCEDURE dbo.usp_GetProfileEligibleCommunityPostForOwner
    @OwnerKey nvarchar(300), @SourceKey nvarchar(128), @SourceRevision nvarchar(128)
  AS
  BEGIN
    SET NOCOUNT ON;
    SELECT CONVERT(nvarchar(128),post.post_key) source_key, app_user.user_key owner_key,
           CONCAT(N''community:v'',post.revision_number) source_revision,
           CONCAT(N''/the-slate/posts/'',CONVERT(nvarchar(36),post.post_key)) canonical_path,
           CONVERT(nvarchar(40),post.published_at_utc,127)+N''+00:00'' published_at, CAST(1 AS bit) profile_eligible
    FROM dbo.community_posts post JOIN dbo.app_users app_user ON app_user.id=post.author_user_id
    WHERE app_user.user_key=@OwnerKey AND CONVERT(nvarchar(128),post.post_key)=@SourceKey
      AND CONCAT(N''community:v'',post.revision_number)=@SourceRevision
      AND post.publication_state=N''published'' AND post.moderation_state=N''clear'' AND post.audience=N''public'';
  END';

  EXEC sys.sp_executesql N'
  CREATE OR ALTER PROCEDURE dbo.usp_GetCurrentProfileEligibleCommunityRevisionForOwner
    @OwnerKey nvarchar(300), @SourceKey nvarchar(128)
  AS
  BEGIN
    SET NOCOUNT ON;
    SELECT CONCAT(N''community:v'',post.revision_number) source_revision
    FROM dbo.community_posts post JOIN dbo.app_users app_user ON app_user.id=post.author_user_id
    WHERE app_user.user_key=@OwnerKey AND CONVERT(nvarchar(128),post.post_key)=@SourceKey
      AND post.publication_state=N''published'' AND post.moderation_state=N''clear'' AND post.audience=N''public'';
  END';

  INSERT dbo.schema_migrations(migration_id, description, application_version)
  VALUES(N'PS-PROFILE-002', N'Governed Profile publication and exact projection references', N'profile-core-d4-v1');

  COMMIT;
END TRY
BEGIN CATCH
  IF XACT_STATE()<>0 ROLLBACK;
  THROW;
END CATCH;
