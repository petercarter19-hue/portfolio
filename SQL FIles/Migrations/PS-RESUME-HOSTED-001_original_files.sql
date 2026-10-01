/* PS-RESUME-HOSTED-001. Proposed private originals and bounded extraction reservations.
   No original bytes or filenames enter SQL. Engine proof and governed application
   remain separate. Existing source/draft/action procedures are not replaced. */
SET NOCOUNT ON;
SET XACT_ABORT ON;
BEGIN TRY
 BEGIN TRANSACTION;
 IF NOT EXISTS (SELECT 1 FROM dbo.schema_migrations WHERE migration_id=N'PS-RESUME-INTAKE-002')
  THROW 52600, 'PS-RESUME-INTAKE-002 must be applied first.', 1;
 IF OBJECT_ID(N'dbo.resume_original_files',N'U') IS NULL
 BEGIN
  CREATE TABLE dbo.resume_original_files (
   original_key uniqueidentifier NOT NULL,
   owner_profile_id bigint NOT NULL,
   source_key uniqueidentifier NOT NULL,
   source_version int NOT NULL,
   blob_name nvarchar(100) NULL,
   blob_etag nvarchar(128) NULL,
   content_type nvarchar(200) NOT NULL,
   byte_length int NOT NULL,
   sha256 char(64) NOT NULL,
   state nvarchar(20) NOT NULL,
   metadata_version int NOT NULL CONSTRAINT DF_resume_original_version DEFAULT 1,
   delete_request_id uniqueidentifier NULL,
   CONSTRAINT CK_resume_original_delete_intent CHECK(state NOT IN(N'delete_pending',N'deleted') OR delete_request_id IS NOT NULL),
   created_at_utc datetime2(7) NOT NULL CONSTRAINT DF_resume_original_created DEFAULT SYSUTCDATETIME(),
   updated_at_utc datetime2(7) NOT NULL CONSTRAINT DF_resume_original_updated DEFAULT SYSUTCDATETIME(),
   CONSTRAINT PK_resume_original_files PRIMARY KEY(original_key),
   CONSTRAINT FK_resume_original_owner FOREIGN KEY(owner_profile_id) REFERENCES dbo.member_profiles(profile_id),
   CONSTRAINT UQ_resume_original_source UNIQUE(owner_profile_id,source_key,source_version),
   CONSTRAINT CK_resume_original_size CHECK(byte_length BETWEEN 1 AND 50000000),
   CONSTRAINT CK_resume_original_version CHECK(source_version>=1 AND metadata_version>=1),
   CONSTRAINT CK_resume_original_digest CHECK(LEN(sha256)=64 AND sha256 NOT LIKE '%[^0-9a-f]%'),
   CONSTRAINT CK_resume_original_type CHECK(content_type IN (N'application/pdf',N'text/plain',N'application/vnd.openxmlformats-officedocument.wordprocessingml.document')),
   CONSTRAINT CK_resume_original_state CHECK(state IN (N'reserved',N'uploaded',N'delete_pending',N'deleted')),
   CONSTRAINT CK_resume_original_path CHECK (
    (state=N'deleted' AND blob_name IS NULL AND blob_etag IS NULL) OR
    (state<>N'deleted' AND LEN(blob_name)=45 AND LEFT(blob_name,10)=N'resume/v1/'
      AND SUBSTRING(blob_name,13,1)=N'/'
      AND SUBSTRING(blob_name,11,2) NOT LIKE '%[^0-9a-f]%'
      AND SUBSTRING(blob_name,14,32) NOT LIKE '%[^0-9a-f]%'
      AND SUBSTRING(blob_name,11,2)=SUBSTRING(blob_name,14,2))),
   CONSTRAINT CK_resume_original_etag CHECK(state<>N'uploaded' OR (blob_etag IS NOT NULL AND LEN(blob_etag)>0))
  );
  CREATE UNIQUE INDEX UX_resume_original_path ON dbo.resume_original_files(blob_name) WHERE blob_name IS NOT NULL;
  CREATE INDEX IX_resume_original_cleanup ON dbo.resume_original_files(state,created_at_utc);
 END;

 EXEC(N'
 CREATE OR ALTER PROCEDURE dbo.usp_GetResumeOriginalFilesForOwner
  @UserKey nvarchar(300), @OriginalKey uniqueidentifier=NULL
 AS
 BEGIN
  SET NOCOUNT ON;
  DECLARE @ProfileId bigint;
  SELECT @ProfileId=p.profile_id FROM dbo.member_profiles p
  JOIN dbo.app_users u ON u.id=p.user_id
  WHERE u.user_key=@UserKey AND u.active=1 AND p.active=1;
  SELECT o.original_key,o.source_key,o.source_version,o.metadata_version AS version,
   o.blob_name,o.blob_etag,o.content_type,o.byte_length,o.sha256,o.state,o.created_at_utc AS created_at,
   CAST(CASE WHEN o.state=N''uploaded'' AND o.blob_etag IS NOT NULL THEN 1 ELSE 0 END AS bit) AS downloadable
  FROM dbo.resume_original_files o
  WHERE o.owner_profile_id=@ProfileId
   AND (@OriginalKey IS NULL OR o.original_key=@OriginalKey)
  ORDER BY o.created_at_utc,o.original_key;
 END;');

 EXEC(N'
 CREATE OR ALTER PROCEDURE dbo.usp_CommitResumeOriginalFileForOwner
  @UserKey nvarchar(300), @CommandJson nvarchar(max)
 AS
 BEGIN
  SET NOCOUNT ON; SET XACT_ABORT ON;
  IF ISJSON(@CommandJson)<>1 THROW 52601,''ORIGINAL_INVALID'',1;
  DECLARE @Type nvarchar(30)=JSON_VALUE(@CommandJson,''$.type''),
   @Key uniqueidentifier=TRY_CONVERT(uniqueidentifier,JSON_VALUE(@CommandJson,''$.original_key'')),
   @Expected int=TRY_CONVERT(int,JSON_VALUE(@CommandJson,''$.expected_version'')),
   @Request uniqueidentifier=TRY_CONVERT(uniqueidentifier,JSON_VALUE(@CommandJson,''$.request_id'')),
   @ProfileId bigint,@Current int,@State nvarchar(20),@PreviousRequest uniqueidentifier,
   @Source uniqueidentifier,@Outcome nvarchar(20)=N''ok'';
  IF @Key IS NULL OR @Type IS NULL OR @Type NOT IN (N''reserve'',N''uploaded'',N''delete'',N''deleted'')
   THROW 52601,''ORIGINAL_INVALID'',1;
  IF EXISTS(SELECT 1 FROM OPENJSON(@CommandJson) WHERE [key] NOT IN (
   ''type'',''original_key'',''source_key'',''source_version'',''blob_name'',''sha256'',''byte_length'',''content_type'',''expected_version'',''blob_etag'',''request_id''))
   THROW 52601,''ORIGINAL_INVALID'',1;
  BEGIN TRY
   BEGIN TRANSACTION;
   SELECT @ProfileId=p.profile_id FROM dbo.member_profiles p WITH(UPDLOCK,HOLDLOCK)
   JOIN dbo.app_users u ON u.id=p.user_id
   WHERE u.user_key=@UserKey AND u.active=1 AND p.active=1;
   IF @ProfileId IS NULL SET @Outcome=N''not_found'';
   ELSE IF @Type=N''reserve''
   BEGIN
    DECLARE @SourceVersion int=TRY_CONVERT(int,JSON_VALUE(@CommandJson,''$.source_version'')),
     @Length int=TRY_CONVERT(int,JSON_VALUE(@CommandJson,''$.byte_length'')),
     @Path nvarchar(100)=JSON_VALUE(@CommandJson,''$.blob_name''),
     @Digest nvarchar(100)=JSON_VALUE(@CommandJson,''$.sha256''),
     @Mime nvarchar(200)=JSON_VALUE(@CommandJson,''$.content_type'');
    SET @Source=TRY_CONVERT(uniqueidentifier,JSON_VALUE(@CommandJson,''$.source_key''));
    IF @Source IS NULL OR @SourceVersion IS NULL OR @SourceVersion<1 OR @Length IS NULL
     OR @Length NOT BETWEEN 1 AND 50000000 OR @Digest IS NULL OR LEN(@Digest)<>64 OR @Digest LIKE ''%[^0-9a-f]%''
     OR @Path IS NULL OR LEN(@Path)<>45 OR LEFT(@Path,10)<>N''resume/v1/''
     OR SUBSTRING(@Path,13,1)<>N''/'' OR SUBSTRING(@Path,11,2) LIKE ''%[^0-9a-f]%''
     OR SUBSTRING(@Path,14,32) LIKE ''%[^0-9a-f]%'' OR SUBSTRING(@Path,11,2)<>SUBSTRING(@Path,14,2)
     OR @Mime IS NULL OR @Mime NOT IN (N''application/pdf'',N''text/plain'',N''application/vnd.openxmlformats-officedocument.wordprocessingml.document'')
      THROW 52601,''ORIGINAL_INVALID'',1;
    IF EXISTS(SELECT 1 FROM dbo.resume_original_files WITH(UPDLOCK,HOLDLOCK) WHERE original_key=@Key
     OR (owner_profile_id=@ProfileId AND source_key=@Source AND source_version=@SourceVersion))
      SET @Outcome=N''conflict'';
    ELSE INSERT dbo.resume_original_files(original_key,owner_profile_id,source_key,source_version,blob_name,content_type,byte_length,sha256,state)
      VALUES(@Key,@ProfileId,@Source,@SourceVersion,@Path,@Mime,@Length,@Digest,N''reserved'');
   END
   ELSE
   BEGIN
    SELECT @Current=metadata_version,@State=state,@Source=source_key,@PreviousRequest=delete_request_id
     FROM dbo.resume_original_files WITH(UPDLOCK,HOLDLOCK) WHERE original_key=@Key AND owner_profile_id=@ProfileId;
    IF @Current IS NULL SET @Outcome=N''not_found'';
    ELSE
    BEGIN
     IF @Type=N''uploaded''
     BEGIN
      DECLARE @Etag nvarchar(200)=JSON_VALUE(@CommandJson,''$.blob_etag'');
      IF @Etag IS NULL OR LEN(@Etag) NOT BETWEEN 1 AND 128 THROW 52601,''ORIGINAL_INVALID'',1;
      IF @Current<>@Expected OR @State NOT IN(N''reserved'',N''delete_pending'') OR @Expected IS NULL
       OR EXISTS(SELECT 1 FROM dbo.resume_original_files WHERE original_key=@Key AND blob_etag IS NOT NULL) SET @Outcome=N''conflict'';
      ELSE UPDATE dbo.resume_original_files SET blob_etag=@Etag,state=CASE WHEN state=N''reserved'' THEN N''uploaded'' ELSE state END,metadata_version=metadata_version+1,updated_at_utc=SYSUTCDATETIME()
       WHERE original_key=@Key AND owner_profile_id=@ProfileId;
     END
     ELSE IF @Type=N''delete''
     BEGIN
      IF @Request IS NULL OR @Expected IS NULL OR @Expected<1 THROW 52601,''ORIGINAL_INVALID'',1;
      ELSE IF @PreviousRequest=@Request AND @State IN(N''delete_pending'',N''deleted'') BEGIN SET @Outcome=N''ok''; END
      ELSE IF @Current<>@Expected SET @Outcome=N''conflict'';
      ELSE IF @State<>N''deleted'' UPDATE dbo.resume_original_files SET state=N''delete_pending'',delete_request_id=@Request,
       metadata_version=metadata_version+1,updated_at_utc=SYSUTCDATETIME() WHERE original_key=@Key AND owner_profile_id=@ProfileId;
     END
     ELSE IF @Type=N''deleted''
     BEGIN
      IF @Expected IS NULL OR @Current<>@Expected OR @State<>N''delete_pending''
       OR NOT EXISTS(SELECT 1 FROM dbo.resume_original_files WHERE original_key=@Key AND blob_etag IS NOT NULL) SET @Outcome=N''conflict'';
      ELSE UPDATE dbo.resume_original_files SET state=N''deleted'',blob_name=NULL,blob_etag=NULL,
       metadata_version=metadata_version+1,updated_at_utc=SYSUTCDATETIME() WHERE original_key=@Key AND owner_profile_id=@ProfileId;
     END;
    END;
   END;
   COMMIT TRANSACTION;
   IF @Outcome<>N''ok'' BEGIN SELECT @Outcome AS outcome; RETURN; END;
   SELECT N''ok'' AS outcome,original_key,source_key,source_version,metadata_version AS version,
    blob_name,blob_etag,content_type,byte_length,sha256,state,created_at_utc AS created_at,CAST(0 AS bit) AS downloadable
   FROM dbo.resume_original_files WHERE original_key=@Key AND owner_profile_id=@ProfileId;
  END TRY
  BEGIN CATCH IF XACT_STATE()<>0 ROLLBACK TRANSACTION; THROW; END CATCH;
 END;');

 EXEC(N'
 CREATE OR ALTER PROCEDURE dbo.usp_ClaimResumeOriginalCleanup @Limit int
 AS
 BEGIN
  SET NOCOUNT ON; SET XACT_ABORT ON;
  IF @Limit IS NULL OR @Limit NOT BETWEEN 1 AND 100 THROW 52601,''ORIGINAL_INVALID'',1;
  BEGIN TRY
   BEGIN TRANSACTION;
   DECLARE @Keys TABLE(original_key uniqueidentifier PRIMARY KEY);
   INSERT @Keys SELECT TOP(@Limit) o.original_key
    FROM dbo.resume_original_files o WITH(UPDLOCK,READPAST)
    WHERE o.state=N''delete_pending'' AND o.delete_request_id IS NOT NULL
    ORDER BY o.created_at_utc,o.original_key;
   SELECT o.original_key,o.source_key,o.source_version,o.metadata_version AS version,o.blob_name,o.blob_etag,
    o.content_type,o.byte_length,o.sha256,o.state,o.created_at_utc AS created_at,CAST(0 AS bit) AS downloadable
    FROM dbo.resume_original_files o JOIN @Keys k ON k.original_key=o.original_key;
   COMMIT TRANSACTION;
  END TRY BEGIN CATCH IF XACT_STATE()<>0 ROLLBACK TRANSACTION; THROW; END CATCH;
 END;');

 EXEC(N'
 CREATE OR ALTER PROCEDURE dbo.usp_CompleteResumeOriginalCleanup @OriginalKey uniqueidentifier,@ExpectedVersion int,@ConfirmedEtag nvarchar(128)
 AS
 BEGIN
  SET NOCOUNT ON; SET XACT_ABORT ON;
  UPDATE dbo.resume_original_files SET state=N''deleted'',blob_name=NULL,blob_etag=NULL,
   metadata_version=metadata_version+1,updated_at_utc=SYSUTCDATETIME()
  WHERE original_key=@OriginalKey AND metadata_version=@ExpectedVersion AND state=N''delete_pending'' AND delete_request_id IS NOT NULL
   AND @ConfirmedEtag IS NOT NULL AND LEN(@ConfirmedEtag)>0 AND (blob_etag IS NULL OR blob_etag=@ConfirmedEtag);
  SELECT CAST(CASE WHEN @@ROWCOUNT=1 THEN 1 ELSE 0 END AS bit) AS completed;
 END;');

/* Insert inside the hosted migration transaction before readiness creation. */
 IF OBJECT_ID(N'dbo.resume_hosted_extraction_budgets',N'U') IS NULL
 BEGIN
  CREATE TABLE dbo.resume_hosted_extraction_budgets (
   scope nvarchar(80) NOT NULL CONSTRAINT PK_resume_hosted_budget PRIMARY KEY,
   maximum_calls int NOT NULL,hard_cap_micro_usd bigint NOT NULL,concurrent_requests int NOT NULL,
   reservation_micro_usd bigint NOT NULL,prepaid_micro_usd bigint NOT NULL CONSTRAINT DF_resume_hosted_prepaid DEFAULT 0,
   dispatched_calls int NOT NULL CONSTRAINT DF_resume_hosted_calls DEFAULT 0,
   CONSTRAINT CK_resume_hosted_budget CHECK(maximum_calls>=1 AND hard_cap_micro_usd>=1 AND concurrent_requests BETWEEN 1 AND maximum_calls
    AND reservation_micro_usd BETWEEN 1 AND hard_cap_micro_usd AND prepaid_micro_usd BETWEEN 0 AND hard_cap_micro_usd
    AND dispatched_calls BETWEEN 0 AND maximum_calls)
  );
  CREATE TABLE dbo.resume_hosted_extraction_reservations (
   scope nvarchar(80) NOT NULL,request_id uniqueidentifier NOT NULL,owner_profile_id bigint NOT NULL,
   state nvarchar(10) NOT NULL,created_at_utc datetime2(7) NOT NULL CONSTRAINT DF_resume_hosted_reserved DEFAULT SYSUTCDATETIME(),
   finished_at_utc datetime2(7) NULL,
   CONSTRAINT PK_resume_hosted_reservation PRIMARY KEY(scope,request_id),
   CONSTRAINT FK_resume_hosted_budget FOREIGN KEY(scope) REFERENCES dbo.resume_hosted_extraction_budgets(scope),
   CONSTRAINT FK_resume_hosted_reservation_owner FOREIGN KEY(owner_profile_id) REFERENCES dbo.member_profiles(profile_id),
   CONSTRAINT CK_resume_hosted_reservation_state CHECK((state=N'active' AND finished_at_utc IS NULL) OR(state=N'finished' AND finished_at_utc IS NOT NULL))
  );
 END;
 EXEC(N'
 CREATE OR ALTER PROCEDURE dbo.usp_ReserveResumeHostedExtractionForOwner
  @UserKey nvarchar(300),@Scope nvarchar(80),@RequestId uniqueidentifier,
  @ReservationMicroUsd bigint,@MaximumCalls int,@HardCapMicroUsd bigint,@ConcurrentRequests int
 AS
 BEGIN
  SET NOCOUNT ON; SET XACT_ABORT ON;
  IF @Scope IS NULL OR LEN(@Scope) NOT BETWEEN 1 AND 80 OR @Scope LIKE ''%[^a-z0-9-]%''
   OR @RequestId IS NULL OR @ReservationMicroUsd IS NULL OR @ReservationMicroUsd<1
   OR @MaximumCalls IS NULL OR @MaximumCalls<1 OR @HardCapMicroUsd IS NULL OR @HardCapMicroUsd<@ReservationMicroUsd
   OR @ConcurrentRequests IS NULL OR @ConcurrentRequests NOT BETWEEN 1 AND @MaximumCalls
    THROW 52620,''EXTRACTION_LIMITS_INVALID'',1;
  DECLARE @ProfileId bigint,@Allowed bit=0;
  BEGIN TRY
   BEGIN TRANSACTION;
   SELECT @ProfileId=p.profile_id FROM dbo.member_profiles p WITH(UPDLOCK,HOLDLOCK)
   JOIN dbo.app_users u ON u.id=p.user_id WHERE u.user_key=@UserKey AND u.active=1 AND p.active=1;
   IF @ProfileId IS NOT NULL
   BEGIN
    IF NOT EXISTS(SELECT 1 FROM dbo.resume_hosted_extraction_budgets WITH(UPDLOCK,HOLDLOCK) WHERE scope=@Scope)
     INSERT dbo.resume_hosted_extraction_budgets(scope,maximum_calls,hard_cap_micro_usd,concurrent_requests,reservation_micro_usd)
      VALUES(@Scope,@MaximumCalls,@HardCapMicroUsd,@ConcurrentRequests,@ReservationMicroUsd);
    IF EXISTS(SELECT 1 FROM dbo.resume_hosted_extraction_budgets WITH(UPDLOCK,HOLDLOCK)
      WHERE scope=@Scope AND maximum_calls=@MaximumCalls AND hard_cap_micro_usd=@HardCapMicroUsd
       AND concurrent_requests=@ConcurrentRequests AND reservation_micro_usd=@ReservationMicroUsd
       AND dispatched_calls<maximum_calls AND prepaid_micro_usd<=hard_cap_micro_usd-@ReservationMicroUsd)
     AND NOT EXISTS(SELECT 1 FROM dbo.resume_hosted_extraction_reservations WHERE scope=@Scope AND request_id=@RequestId)
     AND (SELECT COUNT(*) FROM dbo.resume_hosted_extraction_reservations WHERE scope=@Scope AND state=N''active'')<@ConcurrentRequests
    BEGIN
     INSERT dbo.resume_hosted_extraction_reservations(scope,request_id,owner_profile_id,state) VALUES(@Scope,@RequestId,@ProfileId,N''active'');
     UPDATE dbo.resume_hosted_extraction_budgets SET prepaid_micro_usd=prepaid_micro_usd+@ReservationMicroUsd,dispatched_calls=dispatched_calls+1 WHERE scope=@Scope;
     SET @Allowed=1;
    END;
   END;
   COMMIT TRANSACTION;
   SELECT @Allowed AS reserved;
  END TRY BEGIN CATCH IF XACT_STATE()<>0 ROLLBACK TRANSACTION; THROW; END CATCH;
 END;');
 EXEC(N'
 CREATE OR ALTER PROCEDURE dbo.usp_FinishResumeHostedExtractionForOwner
  @UserKey nvarchar(300),@Scope nvarchar(80),@RequestId uniqueidentifier
 AS
 BEGIN
  SET NOCOUNT ON; SET XACT_ABORT ON;
  DECLARE @ProfileId bigint,@Finished bit=0;
  BEGIN TRY
   BEGIN TRANSACTION;
   SELECT @ProfileId=p.profile_id FROM dbo.member_profiles p WITH(UPDLOCK,HOLDLOCK)
    JOIN dbo.app_users u ON u.id=p.user_id WHERE u.user_key=@UserKey AND u.active=1 AND p.active=1;
   UPDATE dbo.resume_hosted_extraction_reservations SET state=N''finished'',finished_at_utc=SYSUTCDATETIME()
    WHERE scope=@Scope AND request_id=@RequestId AND owner_profile_id=@ProfileId AND state=N''active'';
   IF @@ROWCOUNT=1 SET @Finished=1;
   ELSE IF EXISTS(SELECT 1 FROM dbo.resume_hosted_extraction_reservations WHERE scope=@Scope AND request_id=@RequestId AND owner_profile_id=@ProfileId AND state=N''finished'') SET @Finished=1;
   COMMIT TRANSACTION;
   SELECT @Finished AS finished;
  END TRY BEGIN CATCH IF XACT_STATE()<>0 ROLLBACK TRANSACTION; THROW; END CATCH;
 END;');

 EXEC(N'
 CREATE OR ALTER PROCEDURE dbo.usp_GetResumeHostedReadiness
 AS
 BEGIN
  SET NOCOUNT ON;
  SELECT CAST(CASE WHEN
   EXISTS(SELECT 1 FROM dbo.schema_migrations WHERE migration_id=N''PS-RESUME-INTAKE-002'') AND
   EXISTS(SELECT 1 FROM dbo.schema_migrations WHERE migration_id=N''PS-RESUME-HOSTED-001'') AND
   OBJECT_ID(N''dbo.resume_original_files'',N''U'') IS NOT NULL AND
   OBJECT_ID(N''dbo.resume_hosted_extraction_budgets'',N''U'') IS NOT NULL AND
   OBJECT_ID(N''dbo.usp_ReserveResumeHostedExtractionForOwner'',N''P'') IS NOT NULL AND
   OBJECT_ID(N''dbo.usp_GetResumeIntakeWorkspaceForOwner'',N''P'') IS NOT NULL AND
   OBJECT_ID(N''dbo.usp_CommitResumeOriginalFileForOwner'',N''P'') IS NOT NULL
   THEN 1 ELSE 0 END AS bit) AS schema_ready;
 END;');

 IF NOT EXISTS(SELECT 1 FROM dbo.schema_migrations WHERE migration_id=N'PS-RESUME-HOSTED-001')
 INSERT dbo.schema_migrations(migration_id,description) VALUES(N'PS-RESUME-HOSTED-001',N'Private Resume originals metadata and recoverable Blob lifecycle');
 COMMIT TRANSACTION;
END TRY
BEGIN CATCH IF XACT_STATE()<>0 ROLLBACK TRANSACTION; THROW; END CATCH;
