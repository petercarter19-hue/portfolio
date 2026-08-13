/* Read-only PS-PROFILE-002 structural and owner-isolation verifier. */
SET NOCOUNT ON;
IF NOT EXISTS(SELECT 1 FROM dbo.schema_migrations WHERE migration_id=N'PS-PROFILE-002') THROW 52920,'Missing PS-PROFILE-002 ledger row.',1;
DECLARE @Expected TABLE(name sysname PRIMARY KEY);
INSERT @Expected(name) VALUES
 (N'profile_publications'),(N'profile_content_items'),(N'profile_content_versions'),
 (N'profile_projection_versions'),(N'profile_drafts'),(N'profile_draft_placements'),
 (N'profile_publication_revisions'),(N'profile_publication_revision_items'),
 (N'profile_publication_commands'),(N'profile_slug_history');
IF EXISTS(SELECT 1 FROM @Expected e WHERE OBJECT_ID(N'dbo.'+e.name,N'U') IS NULL) THROW 52921,'Missing PS-PROFILE-002 table.',1;
IF NOT EXISTS(SELECT 1 FROM sys.foreign_keys WHERE name=N'FK_profile_publication_revision_items_revision_owner') THROW 52922,'Missing immutable revision owner fence.',1;
IF NOT EXISTS(SELECT 1 FROM sys.foreign_keys WHERE name=N'FK_profile_draft_placements_projection_owner') THROW 52923,'Missing draft projection owner fence.',1;
IF NOT EXISTS(SELECT 1 FROM sys.foreign_keys WHERE name=N'FK_profile_publications_current_revision') THROW 52926,'Missing current audience revision fence.',1;
IF NOT EXISTS(SELECT 1 FROM sys.foreign_keys WHERE name=N'FK_profile_draft_placements_draft_owner') THROW 52927,'Missing private draft owner fence.',1;
IF NOT EXISTS(SELECT 1 FROM sys.key_constraints WHERE name=N'UQ_profile_publications_owner_audience') THROW 52924,'Missing audience branch uniqueness.',1;
IF NOT EXISTS(SELECT 1 FROM sys.key_constraints WHERE name=N'UQ_profile_slug_history_slug') THROW 52925,'Missing historical slug reservation.',1;
IF OBJECT_ID(N'dbo.usp_GetProfileOwnerBySlug',N'P') IS NULL OR OBJECT_ID(N'dbo.usp_SaveProfileDraftForOwner',N'P') IS NULL OR OBJECT_ID(N'dbo.usp_CommitProfilePublicationForOwner',N'P') IS NULL THROW 52928,'Missing Profile owner-scoped procedures.',1;
DECLARE @SaveDefinition nvarchar(max)=OBJECT_DEFINITION(OBJECT_ID(N'dbo.usp_SaveProfileDraftForOwner'));
DECLARE @PublishDefinition nvarchar(max)=OBJECT_DEFINITION(OBJECT_ID(N'dbo.usp_CommitProfilePublicationForOwner'));
IF @SaveDefinition NOT LIKE N'%@ExpectedDraftVersion%' OR @SaveDefinition NOT LIKE N'%UPDLOCK,HOLDLOCK%'
  THROW 52929,'Missing atomic Profile draft compare-and-swap fence.',1;
IF @SaveDefinition NOT LIKE N'%Latin1_General_100_BIN2%'
  OR @SaveDefinition NOT LIKE N'%JSON_VALUE(@ManifestJson,''$.owner_key'') COLLATE Latin1_General_100_BIN2%'
  OR @SaveDefinition NOT LIKE N'%JSON_VALUE(@ManifestJson,''$.slug'') COLLATE Latin1_General_100_BIN2%'
  OR @SaveDefinition NOT LIKE N'%JSON_VALUE(@ManifestJson,''$.version'') COLLATE Latin1_General_100_BIN2%'
  OR @SaveDefinition NOT LIKE N'%@ExpectedDraftVersion COLLATE Latin1_General_100_BIN2<>@CurrentDraftVersion COLLATE Latin1_General_100_BIN2%'
  OR @SaveDefinition NOT LIKE N'%@CurrentDraftKey COLLATE Latin1_General_100_BIN2<>JSON_VALUE(@ManifestJson,''$.draft_key'') COLLATE Latin1_General_100_BIN2%'
  THROW 52934,'Missing binary exact Profile draft manifest/CAS fence.',1;
IF @PublishDefinition NOT LIKE N'%@ExpectedDraftManifestJson%' OR @PublishDefinition NOT LIKE N'%@ManifestItemCount<>@DraftPlacementCount%'
  THROW 52930,'Missing reviewed Profile manifest/cardinality fence.',1;
IF @PublishDefinition NOT LIKE N'%command.command_key%' OR @PublishDefinition NOT LIKE N'%revision.manifest_json%'
  THROW 52931,'Missing exact stored idempotent command result.',1;
IF @PublishDefinition NOT LIKE N'%@PublicationAction%' OR @PublishDefinition NOT LIKE N'%candidate_native%'
  OR @PublishDefinition NOT LIKE N'%content_kind%' OR @PublishDefinition NOT LIKE N'%source_metadata%'
  OR @PublishDefinition NOT LIKE N'%@PublicationAction=N''withdraw''%'
  OR CHARINDEX(N'candidate_native',@PublishDefinition)>CHARINDEX(N'INSERT dbo.profile_publications',@PublishDefinition)
  THROW 52932,'Missing action-bound Profile publication fence before state mutation.',1;
IF @PublishDefinition NOT LIKE N'%Latin1_General_100_BIN2%'
  OR @PublishDefinition NOT LIKE N'%candidate_native.value COLLATE Latin1_General_100_BIN2%'
  OR @PublishDefinition NOT LIKE N'%item.content_kind COLLATE Latin1_General_100_BIN2%'
  OR @PublishDefinition NOT LIKE N'%item.source_metadata COLLATE Latin1_General_100_BIN2%'
  OR @PublishDefinition NOT LIKE N'%projection.approved_metadata_json COLLATE Latin1_General_100_BIN2%'
  THROW 52933,'Missing binary exact Profile manifest comparison fence.',1;
SELECT CAST(1 AS bit) AS verified, N'PS-PROFILE-002 owner/audience/immutable-reference/concurrency structure present' AS verification;
