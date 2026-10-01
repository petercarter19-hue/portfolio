/*
PS-RESUME-INTAKE-002: private unfinished composer CAS and atomic held-source actions.
Source only until separately governed application. Runtime/rollback acceptance
requires actual disposable SQL proof. No upload/voice policy ceilings are chosen.
Existing Intake001 and canonical migration bytes/procedures remain unchanged.
*/
SET NOCOUNT ON; SET XACT_ABORT ON;
BEGIN TRY
    BEGIN TRANSACTION;
    IF NOT EXISTS(SELECT 1 FROM dbo.schema_migrations WHERE migration_id=N'PS-RESUME-INTAKE-001')
        THROW 52400,'PS-RESUME-INTAKE-001 prerequisite is absent.',1;
    IF OBJECT_ID(N'dbo.resume_intake_composer_state',N'U') IS NULL
        CREATE TABLE dbo.resume_intake_composer_state(
            owner_profile_id bigint NOT NULL,
            revision bigint NOT NULL,
            drafts_json nvarchar(max) NOT NULL,
            updated_at_utc datetime2(7) NOT NULL CONSTRAINT DF_resume_intake_composer_updated DEFAULT SYSUTCDATETIME(),
            CONSTRAINT PK_resume_intake_composer PRIMARY KEY(owner_profile_id),
            CONSTRAINT FK_resume_intake_composer_owner FOREIGN KEY(owner_profile_id) REFERENCES dbo.member_profiles(profile_id),
            CONSTRAINT CK_resume_intake_composer_revision CHECK(revision>=1),
            CONSTRAINT CK_resume_intake_composer_json CHECK(ISJSON(drafts_json)=1)
        );
    IF OBJECT_ID(N'dbo.resume_intake_extracted_actions',N'U') IS NULL
        CREATE TABLE dbo.resume_intake_extracted_actions(
            owner_profile_id bigint NOT NULL,
            override_key uniqueidentifier NOT NULL,
            source_key uniqueidentifier NOT NULL,
            source_version int NOT NULL,
            request_id uniqueidentifier NOT NULL,
            service_digest char(64) NOT NULL,
            created_at_utc datetime2(7) NOT NULL CONSTRAINT DF_resume_intake_actions_created DEFAULT SYSUTCDATETIME(),
            CONSTRAINT PK_resume_intake_extracted_actions PRIMARY KEY(owner_profile_id,override_key),
            CONSTRAINT UQ_resume_intake_extracted_request UNIQUE(owner_profile_id,request_id),
            CONSTRAINT FK_resume_intake_actions_owner FOREIGN KEY(owner_profile_id) REFERENCES dbo.member_profiles(profile_id),
            CONSTRAINT FK_resume_intake_actions_source FOREIGN KEY(source_key) REFERENCES dbo.resume_intake_sources(source_key),
            CONSTRAINT CK_resume_intake_actions_version CHECK(source_version>=1)
        );
    EXEC(N'CREATE OR ALTER PROCEDURE dbo.usp_GetResumeIntakeDurableWorkspaceForOwner @UserKey nvarchar(300)
AS
BEGIN
    SET NOCOUNT ON; SET XACT_ABORT ON;
    SET TRANSACTION ISOLATION LEVEL SERIALIZABLE;
    BEGIN TRY
        BEGIN TRANSACTION;
        DECLARE @ProfileId bigint;
        SELECT @ProfileId=profile.profile_id
        FROM dbo.member_profiles AS profile WITH (UPDLOCK,HOLDLOCK)
        JOIN dbo.app_users AS app_user ON app_user.id=profile.user_id
        WHERE app_user.user_key=@UserKey AND app_user.active=1 AND profile.active=1;
        IF @ProfileId IS NULL THROW 52310,''RESUME_INTAKE_NOT_FOUND'',1;
        DECLARE @Workspace TABLE(workspace_json nvarchar(max));
        INSERT @Workspace EXEC dbo.usp_GetResumeIntakeWorkspaceForOwner @UserKey=@UserKey;
        IF (SELECT COUNT(*) FROM @Workspace)<>1 THROW 52304,''RESUME_INTAKE_VALIDATION'',1;
        DECLARE @Json nvarchar(max)=(SELECT workspace_json FROM @Workspace);
        DECLARE @Drafts nvarchar(max)=N''{}'', @Revision bigint=0;
        SELECT @Drafts=drafts_json,@Revision=revision
        FROM dbo.resume_intake_composer_state WITH (HOLDLOCK)
        WHERE owner_profile_id=@ProfileId;
        SET @Json=JSON_MODIFY(@Json,''$.drafts'',JSON_QUERY(@Drafts));
        SET @Json=JSON_MODIFY(@Json,''$.draft_revision'',@Revision);
        COMMIT TRANSACTION;
        SELECT @Json AS workspace_json;
    END TRY
    BEGIN CATCH
        IF XACT_STATE()<>0 ROLLBACK TRANSACTION;
        THROW;
    END CATCH;
END;');
    EXEC(N'CREATE OR ALTER PROCEDURE dbo.usp_ReplaceResumeIntakeDraftsForOwner
    @UserKey nvarchar(300),@RequestId uniqueidentifier,@CommandJson nvarchar(max)
AS
BEGIN
    SET NOCOUNT ON; SET XACT_ABORT ON;
    SET TRANSACTION ISOLATION LEVEL SERIALIZABLE;
    BEGIN TRY
        BEGIN TRANSACTION;
        DECLARE @ProfileId bigint;
        SELECT @ProfileId=profile.profile_id
        FROM dbo.member_profiles AS profile WITH (UPDLOCK,HOLDLOCK)
        JOIN dbo.app_users AS app_user ON app_user.id=profile.user_id
        WHERE app_user.user_key=@UserKey AND app_user.active=1 AND profile.active=1;
        IF @ProfileId IS NULL THROW 52310,''RESUME_INTAKE_NOT_FOUND'',1;
        IF @RequestId IS NULL OR ISJSON(@CommandJson)<>1
            THROW 52304,''RESUME_INTAKE_VALIDATION'',1;
        IF (SELECT COUNT(*) FROM OPENJSON(@CommandJson))<>3
            OR EXISTS(SELECT 1 FROM OPENJSON(@CommandJson)
                      WHERE [key] NOT IN(N''expected_revision'',N''expected_lifecycle_epoch'',N''drafts''))
            THROW 52304,''RESUME_INTAKE_VALIDATION'',1;
        DECLARE @Expected bigint=TRY_CONVERT(bigint,JSON_VALUE(@CommandJson,''$.expected_revision''));
        DECLARE @ExpectedEpoch int=TRY_CONVERT(int,JSON_VALUE(@CommandJson,''$.expected_lifecycle_epoch''));
        DECLARE @Drafts nvarchar(max)=JSON_QUERY(@CommandJson,''$.drafts'');
        IF NOT EXISTS(SELECT 1 FROM OPENJSON(@CommandJson) WHERE [key]=N''expected_revision'' AND [type]=2)
            OR NOT EXISTS(SELECT 1 FROM OPENJSON(@CommandJson) WHERE [key]=N''expected_lifecycle_epoch'' AND [type]=2)
            OR @Expected IS NULL OR @Expected<0 OR @ExpectedEpoch IS NULL OR @ExpectedEpoch<0
            OR @Drafts IS NULL OR LEFT(LTRIM(@Drafts),1)<>N''{''
            OR (SELECT COUNT(*) FROM OPENJSON(@Drafts))>1
            OR EXISTS(SELECT 1 FROM OPENJSON(@Drafts) WHERE [key]<>N''composer'' OR [type]<>5)
            THROW 52304,''RESUME_INTAKE_VALIDATION'',1;
        IF EXISTS(SELECT 1 FROM OPENJSON(@Drafts))
        BEGIN
            DECLARE @Row nvarchar(max)=JSON_QUERY(@Drafts,''$.composer'');
            IF (SELECT COUNT(*) FROM OPENJSON(@Row))<>10
                OR EXISTS(SELECT 1 FROM OPENJSON(@Row) WHERE [key] NOT IN
                    (N''draft_key'',N''version'',N''state'',N''text'',N''items'',N''attachments'',
                     N''created_at'',N''updated_at'',N''expires_at'',N''last_request_id''))
                THROW 52304,''RESUME_INTAKE_VALIDATION'',1;
            -- Ten declared fields; duplicates are refused independently below.
            IF EXISTS(SELECT [key] FROM OPENJSON(@Row) GROUP BY [key] HAVING COUNT(*)<>1)
                OR JSON_VALUE(@Row,''$.draft_key'') IS NULL OR JSON_VALUE(@Row,''$.draft_key'')<>N''composer''
                OR JSON_VALUE(@Row,''$.state'') IS NULL OR JSON_VALUE(@Row,''$.state'')<>N''active''
                OR NOT EXISTS(SELECT 1 FROM OPENJSON(@Row) WHERE [key]=N''version'' AND [type]=2)
                OR TRY_CONVERT(bigint,JSON_VALUE(@Row,''$.version'')) IS NULL
                OR TRY_CONVERT(bigint,JSON_VALUE(@Row,''$.version''))<1
                OR NOT EXISTS(SELECT 1 FROM OPENJSON(@Row) WHERE [key]=N''text'' AND [type] IN(0,1))
                OR NOT EXISTS(SELECT 1 FROM OPENJSON(@Row) WHERE [key]=N''items'' AND [type]=4)
                OR NOT EXISTS(SELECT 1 FROM OPENJSON(@Row) WHERE [key]=N''attachments'' AND [type]=4)
                OR TRY_CONVERT(uniqueidentifier,JSON_VALUE(@Row,''$.last_request_id'')) IS NULL
                OR TRY_CONVERT(datetimeoffset,JSON_VALUE(@Row,''$.created_at'')) IS NULL
                OR TRY_CONVERT(datetimeoffset,JSON_VALUE(@Row,''$.updated_at'')) IS NULL
                OR (JSON_VALUE(@Row,''$.expires_at'') IS NOT NULL
                    AND TRY_CONVERT(datetimeoffset,JSON_VALUE(@Row,''$.expires_at'')) IS NULL)
                THROW 52304,''RESUME_INTAKE_VALIDATION'',1;
        END;
        DECLARE @Current bigint=0,@Epoch int=0;
        SELECT @Current=revision FROM dbo.resume_intake_composer_state WITH (UPDLOCK,HOLDLOCK)
        WHERE owner_profile_id=@ProfileId;
        SELECT @Epoch=lifecycle_epoch FROM dbo.resume_intake_owner_state WITH (UPDLOCK,HOLDLOCK)
        WHERE owner_profile_id=@ProfileId;
        IF @Current<>@Expected OR @Epoch<>@ExpectedEpoch
        BEGIN
            COMMIT TRANSACTION;
            SELECT N''conflict'' AS outcome,CONVERT(nvarchar(36),@RequestId) AS request_id,@Current AS revision;
            RETURN;
        END;
        IF @Current=9223372036854775807 THROW 52304,''RESUME_INTAKE_VALIDATION'',1;
        IF @Row IS NOT NULL AND TRY_CONVERT(bigint,JSON_VALUE(@Row,''$.version''))>@Current+1
            THROW 52304,''RESUME_INTAKE_VALIDATION'',1;
        IF EXISTS(SELECT 1 FROM dbo.resume_intake_composer_state WHERE owner_profile_id=@ProfileId)
            UPDATE dbo.resume_intake_composer_state SET revision=@Current+1,drafts_json=@Drafts,
                updated_at_utc=SYSUTCDATETIME() WHERE owner_profile_id=@ProfileId;
        ELSE
            INSERT dbo.resume_intake_composer_state(owner_profile_id,revision,drafts_json)
            VALUES(@ProfileId,@Current+1,@Drafts);
        -- Retain the empty row/revision after discard or expiry to prevent ABA.
        COMMIT TRANSACTION;
        SELECT N''applied'' AS outcome,CONVERT(nvarchar(36),@RequestId) AS request_id,@Current+1 AS revision;
    END TRY
    BEGIN CATCH
        IF XACT_STATE()<>0 ROLLBACK TRANSACTION;
        THROW;
    END CATCH;
END;');
    EXEC(N'CREATE OR ALTER PROCEDURE dbo.usp_CommitResumeIntakeExtractedSourceForOwner
    @UserKey nvarchar(300),@RequestId uniqueidentifier,@CommandJson nvarchar(max)
AS
BEGIN
    SET NOCOUNT ON; SET XACT_ABORT ON;
    SET TRANSACTION ISOLATION LEVEL SERIALIZABLE;
    BEGIN TRY
        BEGIN TRANSACTION;
        DECLARE @ProfileId bigint;
        SELECT @ProfileId=profile.profile_id
        FROM dbo.member_profiles AS profile WITH (UPDLOCK,HOLDLOCK)
        JOIN dbo.app_users AS app_user ON app_user.id=profile.user_id
        WHERE app_user.user_key=@UserKey AND app_user.active=1 AND profile.active=1;
        IF @ProfileId IS NULL THROW 52310,''RESUME_INTAKE_NOT_FOUND'',1;
        IF @RequestId IS NULL OR ISJSON(@CommandJson)<>1
            THROW 52304,''RESUME_INTAKE_VALIDATION'',1;
        IF (SELECT COUNT(*) FROM OPENJSON(@CommandJson))<>3
            OR EXISTS(SELECT 1 FROM OPENJSON(@CommandJson)
                      WHERE [key] NOT IN(N''type'',N''source_binding'',N''submission''))
            OR JSON_VALUE(@CommandJson,''$.type'') IS NULL OR JSON_VALUE(@CommandJson,''$.type'')<>N''keep_extracted_separate''
            THROW 52304,''RESUME_INTAKE_VALIDATION'',1;
        DECLARE @Binding nvarchar(max)=JSON_QUERY(@CommandJson,''$.source_binding'');
        DECLARE @Submission nvarchar(max)=JSON_QUERY(@CommandJson,''$.submission'');
        IF @Binding IS NULL OR @Submission IS NULL
            OR (SELECT COUNT(*) FROM OPENJSON(@Binding))<>4
            OR EXISTS(SELECT 1 FROM OPENJSON(@Binding)
                      WHERE [key] NOT IN(N''source_key'',N''source_version'',N''override_key'',N''record_type''))
            THROW 52304,''RESUME_INTAKE_VALIDATION'',1;
        DECLARE @SourceKey uniqueidentifier=TRY_CONVERT(uniqueidentifier,JSON_VALUE(@Binding,''$.source_key''));
        DECLARE @SourceVersion int=TRY_CONVERT(int,JSON_VALUE(@Binding,''$.source_version''));
        DECLARE @Override uniqueidentifier=TRY_CONVERT(uniqueidentifier,JSON_VALUE(@Binding,''$.override_key''));
        DECLARE @RecordType nvarchar(30)=JSON_VALUE(@Binding,''$.record_type'');
        DECLARE @Digest char(64)=JSON_VALUE(@Submission,''$.request_digest'');
        IF @SourceKey IS NULL OR @SourceVersion IS NULL OR @SourceVersion<1 OR @Override IS NULL
            OR @RecordType IS NULL OR @RecordType NOT IN(N''role'',N''education'',N''credential'',N''skill'',N''accomplishment'')
            OR @Digest IS NULL OR LEN(@Digest)<>64
            OR @Digest LIKE ''%[^0-9a-f]%'' COLLATE Latin1_General_100_BIN2
            OR TRY_CONVERT(uniqueidentifier,JSON_VALUE(@Submission,''$.request_id'')) IS NULL
            OR TRY_CONVERT(uniqueidentifier,JSON_VALUE(@Submission,''$.request_id''))<>@RequestId
            OR TRY_CONVERT(uniqueidentifier,JSON_VALUE(@Submission,''$.submission_key'')) IS NULL
            OR TRY_CONVERT(uniqueidentifier,JSON_VALUE(@Submission,''$.submission_key''))<>@Override
            OR JSON_VALUE(@Submission,''$.type'') IS NULL OR JSON_VALUE(@Submission,''$.type'')<>N''add_submission''
            THROW 52304,''RESUME_INTAKE_VALIDATION'',1;
        DECLARE @ExistingDigest char(64),@Result nvarchar(max),@Winner uniqueidentifier;
        SELECT @ExistingDigest=service_digest,@Result=result_json
        FROM dbo.resume_intake_command_receipts WITH (UPDLOCK,HOLDLOCK)
        WHERE owner_profile_id=@ProfileId AND request_id=@RequestId;
        IF @ExistingDigest IS NOT NULL
        BEGIN
            IF @ExistingDigest<>@Digest
                OR TRY_CONVERT(uniqueidentifier,JSON_VALUE(@Result,''$.submission.submission_key'')) IS NULL
                OR TRY_CONVERT(uniqueidentifier,JSON_VALUE(@Result,''$.submission.submission_key''))<>@Override
                THROW 52303,''RESUME_INTAKE_IDEMPOTENCY_CONFLICT'',1;
            -- Same-key history replays only its structural receipt. Hydration
            -- reads current active sources and cannot restore purged wording.
            COMMIT TRANSACTION;
            SELECT CONVERT(bit,1) AS committed,CONVERT(bit,1) AS replayed,
                @Digest AS request_digest,@Result AS result_json,
                CONVERT(nvarchar(36),@RequestId) AS receipt_request_id;
            RETURN;
        END;
        DECLARE @Json nvarchar(max),@State nvarchar(20),@Version int;
        SELECT @Json=structured_values_json,@State=state,@Version=source_version
        FROM dbo.resume_intake_sources WITH (UPDLOCK,HOLDLOCK)
        WHERE owner_profile_id=@ProfileId AND source_key=@SourceKey;
        IF @State IS NULL THROW 52310,''RESUME_INTAKE_NOT_FOUND'',1;
        IF @State<>N''active'' OR @Version<>@SourceVersion OR @Json IS NULL
            THROW 52302,''RESUME_INTAKE_CHANGED'',1;
        DECLARE @Index int,@Candidate nvarchar(max);
        IF (SELECT COUNT(*) FROM OPENJSON(@Json,''$._extracted_candidates'')
            WHERE TRY_CONVERT(uniqueidentifier,JSON_VALUE([value],''$.override_key''))=@Override)<>1
            THROW 52302,''RESUME_INTAKE_CHANGED'',1;
        SELECT @Index=TRY_CONVERT(int,[key]),@Candidate=[value]
        FROM OPENJSON(@Json,''$._extracted_candidates'')
        WHERE TRY_CONVERT(uniqueidentifier,JSON_VALUE([value],''$.override_key''))=@Override;
        IF @Index IS NULL
            OR TRY_CONVERT(uniqueidentifier,JSON_VALUE(@Candidate,''$.source_key'')) IS NULL
            OR TRY_CONVERT(uniqueidentifier,JSON_VALUE(@Candidate,''$.source_key''))<>@SourceKey
            OR TRY_CONVERT(int,JSON_VALUE(@Candidate,''$.source_version'')) IS NULL
            OR TRY_CONVERT(int,JSON_VALUE(@Candidate,''$.source_version''))<>@Version
            OR JSON_VALUE(@Candidate,''$.record_type'') IS NULL OR JSON_VALUE(@Candidate,''$.record_type'')<>@RecordType
            THROW 52302,''RESUME_INTAKE_CHANGED'',1;
        SELECT @Winner=request_id,@ExistingDigest=service_digest
        FROM dbo.resume_intake_extracted_actions WITH (UPDLOCK,HOLDLOCK)
        WHERE owner_profile_id=@ProfileId AND override_key=@Override
            AND source_key=@SourceKey AND source_version=@Version;
        IF @Winner IS NOT NULL
        BEGIN
            IF @ExistingDigest<>@Digest THROW 52303,''RESUME_INTAKE_IDEMPOTENCY_CONFLICT'',1;
            SELECT @Result=result_json FROM dbo.resume_intake_command_receipts
            WHERE owner_profile_id=@ProfileId AND request_id=@Winner;
            IF @Result IS NULL THROW 52304,''RESUME_INTAKE_VALIDATION'',1;
            COMMIT TRANSACTION;
            SELECT CONVERT(bit,1) AS committed,CONVERT(bit,1) AS replayed,
                @Digest AS request_digest,@Result AS result_json,
                CONVERT(nvarchar(36),@Winner) AS receipt_request_id;
            RETURN;
        END;
        IF JSON_VALUE(@Candidate,''$.state'') IS NULL OR JSON_VALUE(@Candidate,''$.state'')<>N''pending''
            THROW 52302,''RESUME_INTAKE_CHANGED'',1;
        DECLARE @Epoch int=0,@Policy int=0;
        SELECT @Epoch=lifecycle_epoch,@Policy=policy_version
        FROM dbo.resume_intake_owner_state WITH (UPDLOCK,HOLDLOCK) WHERE owner_profile_id=@ProfileId;
        IF TRY_CONVERT(int,JSON_VALUE(@Submission,''$.lifecycle_epoch'')) IS NULL
            OR TRY_CONVERT(int,JSON_VALUE(@Submission,''$.lifecycle_epoch''))<>@Epoch
            OR TRY_CONVERT(int,JSON_VALUE(@Submission,''$.policy_version'')) IS NULL
            OR TRY_CONVERT(int,JSON_VALUE(@Submission,''$.policy_version''))<@Policy
            THROW 52302,''RESUME_INTAKE_CHANGED'',1;
        DECLARE @Expected nvarchar(max)=JSON_QUERY(@Candidate,''$.canonical_values'');
        DECLARE @Actual nvarchar(max);
        DECLARE @Intents nvarchar(max)=JSON_QUERY(@Submission,''$.canonical_intents'');
        DECLARE @Sources nvarchar(max)=JSON_QUERY(@Submission,''$.sources'');
        DECLARE @Proposals nvarchar(max)=JSON_QUERY(@Submission,''$.proposals'');
        DECLARE @Intent nvarchar(max),@Inner nvarchar(max);
        IF @Expected IS NULL OR LEFT(LTRIM(@Expected),1)<>N''{''
            OR NOT EXISTS(SELECT 1 FROM OPENJSON(@Expected))
            OR @Intents IS NULL OR @Sources IS NULL OR @Proposals IS NULL
            OR (SELECT COUNT(*) FROM OPENJSON(@Sources))<>1
            THROW 52304,''RESUME_INTAKE_VALIDATION'',1;
        DECLARE @NewSource uniqueidentifier=TRY_CONVERT(uniqueidentifier,JSON_VALUE(@Sources,''$[0].source_key''));
        DECLARE @NewValues nvarchar(max)=JSON_QUERY(@Sources,''$[0].structured_values'');
        IF @NewSource IS NULL OR @NewSource=@SourceKey OR @NewValues IS NULL
            OR JSON_VALUE(@Sources,''$[0].kind'') IS NULL OR JSON_VALUE(@Sources,''$[0].kind'')<>N''structured''
            OR JSON_VALUE(@Sources,''$[0].state'') IS NULL OR JSON_VALUE(@Sources,''$[0].state'')<>N''active''
            OR TRY_CONVERT(int,JSON_VALUE(@Sources,''$[0].version'')) IS NULL
            OR TRY_CONVERT(int,JSON_VALUE(@Sources,''$[0].version''))<>1
            OR JSON_VALUE(@Sources,''$[0].text'') IS NOT NULL
            OR EXISTS(SELECT [key] FROM OPENJSON(@NewValues) GROUP BY [key] HAVING COUNT(*)<>1)
            OR EXISTS(
                SELECT 1 FROM OPENJSON(@Expected) e FULL JOIN OPENJSON(@NewValues) a
                ON e.[key] COLLATE Latin1_General_100_BIN2=a.[key] COLLATE Latin1_General_100_BIN2
                WHERE e.[key] IS NULL OR a.[key] IS NULL OR e.[type]<>a.[type]
                    OR DATALENGTH(e.[value])<>DATALENGTH(a.[value])
                    OR e.[value] COLLATE Latin1_General_100_BIN2<>a.[value] COLLATE Latin1_General_100_BIN2)
            THROW 52304,''RESUME_INTAKE_VALIDATION'',1;
        IF (SELECT COUNT(*) FROM OPENJSON(@Intents))=1
        BEGIN
            IF (SELECT COUNT(*) FROM OPENJSON(@Proposals))<>0
                THROW 52304,''RESUME_INTAKE_VALIDATION'',1;
            SET @Intent=JSON_QUERY(@Intents,''$[0]'');
            SET @Inner=JSON_QUERY(@Intent,''$.command'');
            IF @Intent IS NULL OR @Inner IS NULL
                OR (SELECT COUNT(*) FROM OPENJSON(@Intent))<>4
                OR EXISTS(SELECT 1 FROM OPENJSON(@Intent) WHERE [key] NOT IN(N''boundary'',N''request_id'',N''procedure'',N''command''))
                OR TRY_CONVERT(uniqueidentifier,JSON_VALUE(@Intent,''$.request_id'')) IS NULL
                OR TRY_CONVERT(uniqueidentifier,JSON_VALUE(@Inner,''$.command_id'')) IS NULL
                OR TRY_CONVERT(uniqueidentifier,JSON_VALUE(@Intent,''$.request_id''))<>TRY_CONVERT(uniqueidentifier,JSON_VALUE(@Inner,''$.command_id''))
                OR JSON_VALUE(@Intent,''$.boundary'') IS NULL OR JSON_VALUE(@Intent,''$.boundary'')<>N''living_resume''
                OR JSON_VALUE(@Intent,''$.procedure'') IS NULL OR JSON_VALUE(@Intent,''$.procedure'')<>N''usp_CommitLivingResumeCommandForOwner''
                OR JSON_VALUE(@Inner,''$.type'') IS NULL OR JSON_VALUE(@Inner,''$.type'')<>N''create_''+@RecordType
                OR @RecordType=N''accomplishment''
                OR JSON_VALUE(@Inner,''$.parent_key'') IS NOT NULL
                OR JSON_VALUE(@Inner,''$.expected_version'') IS NOT NULL
                THROW 52304,''RESUME_INTAKE_VALIDATION'',1;
            SET @Actual=JSON_QUERY(@Inner,''$.values'');
            IF JSON_QUERY(@Sources,''$[0].structured_values'') IS NULL
                THROW 52304,''RESUME_INTAKE_VALIDATION'',1;
        END
        ELSE IF (SELECT COUNT(*) FROM OPENJSON(@Intents))=0 AND @RecordType=N''accomplishment''
        BEGIN
            IF (SELECT COUNT(*) FROM OPENJSON(@Proposals))<>1
                OR JSON_VALUE(@Proposals,''$[0].record_type'') IS NULL OR JSON_VALUE(@Proposals,''$[0].record_type'')<>N''accomplishment''
                OR JSON_VALUE(@Proposals,''$[0].kind'') IS NULL OR JSON_VALUE(@Proposals,''$[0].kind'')<>N''ambiguous_match''
                OR JSON_VALUE(@Proposals,''$[0].target_key'') IS NOT NULL
                THROW 52304,''RESUME_INTAKE_VALIDATION'',1;
            -- An Impact without a selected parent remains a proposal; do not
            -- invent a parent or silently create canonical truth.
            -- The keep command stages the complete editor-normalized values,
            -- including null metric fields. Bind that same complete object.
            SET @Actual=JSON_QUERY(@Proposals,''$[0].proposed_values'');
            IF @Actual IS NULL
                OR EXISTS(SELECT [key] FROM OPENJSON(@Actual) GROUP BY [key] HAVING COUNT(*)<>1)
                OR EXISTS(
                SELECT 1 FROM OPENJSON(@Expected) e FULL JOIN OPENJSON(@Actual) a
                ON e.[key] COLLATE Latin1_General_100_BIN2=a.[key] COLLATE Latin1_General_100_BIN2
                WHERE e.[key] IS NULL OR a.[key] IS NULL OR e.[type]<>a.[type]
                    OR DATALENGTH(e.[value])<>DATALENGTH(a.[value])
                    OR e.[value] COLLATE Latin1_General_100_BIN2<>a.[value] COLLATE Latin1_General_100_BIN2)
                THROW 52304,''RESUME_INTAKE_VALIDATION'',1;
            SET @Actual=NULL;
        END
        ELSE THROW 52304,''RESUME_INTAKE_VALIDATION'',1;
        IF @Inner IS NOT NULL AND (@Actual IS NULL OR EXISTS(
            SELECT 1 FROM OPENJSON(@Expected) e FULL JOIN OPENJSON(@Actual) a
            ON e.[key] COLLATE Latin1_General_100_BIN2=a.[key] COLLATE Latin1_General_100_BIN2
            WHERE e.[key] IS NULL OR a.[key] IS NULL OR e.[type]<>a.[type]
                OR DATALENGTH(e.[value])<>DATALENGTH(a.[value])
                OR e.[value] COLLATE Latin1_General_100_BIN2<>a.[value] COLLATE Latin1_General_100_BIN2))
            THROW 52304,''RESUME_INTAKE_VALIDATION'',1;
        IF EXISTS(SELECT [key] FROM OPENJSON(@Candidate,''$.canonical_values'') GROUP BY [key] HAVING COUNT(*)<>1)
            OR (@Inner IS NOT NULL AND EXISTS(SELECT [key] FROM OPENJSON(@Actual) GROUP BY [key] HAVING COUNT(*)<>1))
            THROW 52304,''RESUME_INTAKE_VALIDATION'',1;
        -- The established submission procedure owns its nested transaction,
        -- leaving this outer owner/source transaction open until consumption.
        EXEC dbo.usp_CommitResumeIntakeSubmissionForOwner
            @UserKey=@UserKey,@RequestId=@RequestId,@CommandJson=@Submission;
        DECLARE @Path nvarchar(200)=N''$._extracted_candidates[''+CONVERT(nvarchar(20),@Index)+N'']'';
        SET @Json=JSON_MODIFY(@Json,@Path+N''.state'',N''consumed'');
        SET @Json=JSON_MODIFY(@Json,@Path+N''.consumed_request_id'',CONVERT(nvarchar(36),@RequestId));
        SET @Json=JSON_MODIFY(@Json,@Path+N''.values'',NULL);
        SET @Json=JSON_MODIFY(@Json,@Path+N''.canonical_values'',NULL);
        UPDATE dbo.resume_intake_sources SET structured_values_json=@Json
        WHERE owner_profile_id=@ProfileId AND source_key=@SourceKey AND source_version=@Version AND state=N''active'';
        IF @@ROWCOUNT<>1 THROW 52302,''RESUME_INTAKE_CHANGED'',1;
        INSERT dbo.resume_intake_extracted_actions
            (owner_profile_id,override_key,source_key,source_version,request_id,service_digest)
        VALUES(@ProfileId,@Override,@SourceKey,@Version,@RequestId,@Digest);
        COMMIT TRANSACTION;
        SELECT CONVERT(bit,1) AS committed,CONVERT(bit,0) AS replayed,@Digest AS request_digest,
            CONVERT(nvarchar(36),@RequestId) AS receipt_request_id;
    END TRY
    BEGIN CATCH
        IF XACT_STATE()<>0 ROLLBACK TRANSACTION;
        THROW;
    END CATCH;
END;');
    IF NOT EXISTS(SELECT 1 FROM dbo.schema_migrations WHERE migration_id=N'PS-RESUME-INTAKE-002')
        INSERT dbo.schema_migrations(migration_id,description)
        VALUES(N'PS-RESUME-INTAKE-002',N'Owner composer revision CAS and atomic extracted-source consumption');
    COMMIT TRANSACTION;
END TRY
BEGIN CATCH
    IF XACT_STATE()<>0 ROLLBACK TRANSACTION;
    THROW;
END CATCH;
