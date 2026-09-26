/*
Rollback for proposed PS-RESUME-PUBLICATION-001. Refuses populated publication
state before changing any object. Restores replaced owner
command procedures from their Core copies. Does not drop catalog, draft,
or original entry-policy objects.
*/
SET NOCOUNT ON;
SET XACT_ABORT ON;

BEGIN TRY
    BEGIN TRANSACTION;

    IF OBJECT_ID(N'dbo.resume_sharing_state', N'U') IS NOT NULL
       AND EXISTS (SELECT 1 FROM dbo.resume_sharing_state WITH (UPDLOCK, HOLDLOCK))
        THROW 54120, 'Rollback refused: publication state is populated.', 1;
    IF OBJECT_ID(N'dbo.resume_publication_revisions', N'U') IS NOT NULL
       AND EXISTS (SELECT 1 FROM dbo.resume_publication_revisions WITH (UPDLOCK, HOLDLOCK))
        THROW 54120, 'Rollback refused: publication state is populated.', 1;
    IF OBJECT_ID(N'dbo.resume_publication_evidence', N'U') IS NOT NULL
       AND EXISTS (SELECT 1 FROM dbo.resume_publication_evidence WITH (UPDLOCK, HOLDLOCK))
        THROW 54120, 'Rollback refused: publication state is populated.', 1;
    IF OBJECT_ID(N'dbo.resume_publication_receipts', N'U') IS NOT NULL
       AND EXISTS (SELECT 1 FROM dbo.resume_publication_receipts WITH (UPDLOCK, HOLDLOCK))
        THROW 54120, 'Rollback refused: publication state is populated.', 1;
    IF OBJECT_ID(N'dbo.resume_publication_outbox', N'U') IS NOT NULL
       AND EXISTS (SELECT 1 FROM dbo.resume_publication_outbox WITH (UPDLOCK, HOLDLOCK))
        THROW 54120, 'Rollback refused: publication state is populated.', 1;
    IF OBJECT_ID(N'dbo.resume_publication_core_execute_permissions', N'U') IS NULL
        THROW 54121, 'Rollback refused: predecessor permissions are unavailable.', 1;

    IF OBJECT_ID(N'dbo.usp_CommitResumePublicationCommandForOwner', N'P') IS NOT NULL
        DROP PROCEDURE dbo.usp_CommitResumePublicationCommandForOwner;
    IF OBJECT_ID(N'dbo.usp_GetResumePublicationForOwner', N'P') IS NOT NULL
        DROP PROCEDURE dbo.usp_GetResumePublicationForOwner;
    IF OBJECT_ID(N'dbo.usp_GetResumePublicationReceiptForOwner', N'P') IS NOT NULL
        DROP PROCEDURE dbo.usp_GetResumePublicationReceiptForOwner;
    IF OBJECT_ID(N'dbo.usp_GetPublicResumePublicationBySlug', N'P') IS NOT NULL
        DROP PROCEDURE dbo.usp_GetPublicResumePublicationBySlug;
    IF OBJECT_ID(N'dbo.usp_GetResumePublicationMediaAuthorization', N'P') IS NOT NULL
        DROP PROCEDURE dbo.usp_GetResumePublicationMediaAuthorization;
    IF OBJECT_ID(N'dbo.usp_ListEntryPolicyEntriesForOwnerCore', N'P') IS NOT NULL
    BEGIN
        DROP PROCEDURE dbo.usp_ListEntryPolicyEntriesForOwner;
        EXEC sys.sp_rename N'dbo.usp_ListEntryPolicyEntriesForOwnerCore', N'usp_ListEntryPolicyEntriesForOwner';
    END;
    IF OBJECT_ID(N'dbo.usp_GetEntryPolicyEntryForOwnerCore', N'P') IS NOT NULL
    BEGIN
        DROP PROCEDURE dbo.usp_GetEntryPolicyEntryForOwner;
        EXEC sys.sp_rename N'dbo.usp_GetEntryPolicyEntryForOwnerCore', N'usp_GetEntryPolicyEntryForOwner';
    END;
    IF OBJECT_ID(N'dbo.usp_ListResumePublicationPolicyForOwner', N'P') IS NOT NULL
        DROP PROCEDURE dbo.usp_ListResumePublicationPolicyForOwner;
    IF OBJECT_ID(N'dbo.usp_ResumePublicationApplyCanonicalInternal', N'P') IS NOT NULL
        DROP PROCEDURE dbo.usp_ResumePublicationApplyCanonicalInternal;
    IF OBJECT_ID(N'dbo.usp_ResumePublicationRefreshProjectionInternal', N'P') IS NOT NULL
        DROP PROCEDURE dbo.usp_ResumePublicationRefreshProjectionInternal;
    IF OBJECT_ID(N'dbo.usp_ResumePublicationEncodeSourceInternal', N'P') IS NOT NULL
        DROP PROCEDURE dbo.usp_ResumePublicationEncodeSourceInternal;
    IF OBJECT_ID(N'dbo.usp_ResumePublicationLockOwnerInternal', N'P') IS NOT NULL
        DROP PROCEDURE dbo.usp_ResumePublicationLockOwnerInternal;
    IF OBJECT_ID(N'dbo.usp_ResumePublicationBuildManifestsInternal', N'P') IS NOT NULL
        DROP PROCEDURE dbo.usp_ResumePublicationBuildManifestsInternal;
    IF OBJECT_ID(N'dbo.usp_ResumePublicationGuardLegacyMutator', N'P') IS NOT NULL
        DROP PROCEDURE dbo.usp_ResumePublicationGuardLegacyMutator;
    IF OBJECT_ID(N'dbo.usp_ResumePublicationApplyAfterPolicyInternal', N'P') IS NOT NULL
        DROP PROCEDURE dbo.usp_ResumePublicationApplyAfterPolicyInternal;

    IF OBJECT_ID(N'dbo.usp_CommitEntryPolicyCommandForOwner', N'P') IS NOT NULL
        DROP PROCEDURE dbo.usp_CommitEntryPolicyCommandForOwner;
    IF OBJECT_ID(N'dbo.usp_CommitEntryPolicyCommandForOwnerCore', N'P') IS NOT NULL
        EXEC sys.sp_rename N'dbo.usp_CommitEntryPolicyCommandForOwnerCore', N'usp_CommitEntryPolicyCommandForOwner';

    IF OBJECT_ID(N'dbo.usp_CommitResumeDraftCommandForOwner', N'P') IS NOT NULL
       AND OBJECT_ID(N'dbo.usp_CommitResumeDraftCommandForOwnerCore', N'P') IS NOT NULL
    BEGIN
        DROP PROCEDURE dbo.usp_CommitResumeDraftCommandForOwner;
        EXEC sys.sp_rename N'dbo.usp_CommitResumeDraftCommandForOwnerCore', N'usp_CommitResumeDraftCommandForOwner';
    END;

    IF OBJECT_ID(N'dbo.usp_CommitResumeMediaCommandForOwner', N'P') IS NOT NULL
       AND OBJECT_ID(N'dbo.usp_CommitResumeMediaCommandForOwnerCore', N'P') IS NOT NULL
    BEGIN
        DROP PROCEDURE dbo.usp_CommitResumeMediaCommandForOwner;
        EXEC sys.sp_rename N'dbo.usp_CommitResumeMediaCommandForOwnerCore', N'usp_CommitResumeMediaCommandForOwner';
    END;

    IF OBJECT_ID(N'dbo.usp_CommitResumeIntakeCommandForOwner', N'P') IS NOT NULL
       AND OBJECT_ID(N'dbo.usp_CommitResumeIntakeCommandForOwnerCore', N'P') IS NOT NULL
    BEGIN
        DROP PROCEDURE dbo.usp_CommitResumeIntakeCommandForOwner;
        EXEC sys.sp_rename N'dbo.usp_CommitResumeIntakeCommandForOwnerCore', N'usp_CommitResumeIntakeCommandForOwner';
    END;

    IF OBJECT_ID(N'dbo.usp_CommitLivingResumeCommandForOwner', N'P') IS NOT NULL
       AND OBJECT_ID(N'dbo.usp_CommitLivingResumeCommandForOwnerCore', N'P') IS NOT NULL
    BEGIN
        DROP PROCEDURE dbo.usp_CommitLivingResumeCommandForOwner;
        EXEC sys.sp_rename N'dbo.usp_CommitLivingResumeCommandForOwnerCore', N'usp_CommitLivingResumeCommandForOwner';
    END;

    -- The Core DENY follows its object through sp_rename. Remove it, then
    -- restore only the predecessor's captured explicit PUBLIC permission.
    DECLARE @ProcedureName sysname, @PermissionState char(1), @PermissionSql nvarchar(max);
    DECLARE predecessor_permissions CURSOR LOCAL FAST_FORWARD FOR
        SELECT procedure_name, permission_state
          FROM dbo.resume_publication_core_execute_permissions
         ORDER BY procedure_name;
    OPEN predecessor_permissions;
    FETCH NEXT FROM predecessor_permissions INTO @ProcedureName, @PermissionState;
    WHILE @@FETCH_STATUS = 0
    BEGIN
        IF OBJECT_ID(N'dbo.' + @ProcedureName, N'P') IS NULL
            THROW 54122, 'Rollback refused: predecessor procedure is unavailable.', 1;
        SET @PermissionSql = N'REVOKE EXECUTE ON OBJECT::dbo.' + QUOTENAME(@ProcedureName) + N' FROM PUBLIC;';
        EXEC sys.sp_executesql @PermissionSql;
        IF @PermissionState = 'G'
            SET @PermissionSql = N'GRANT EXECUTE ON OBJECT::dbo.' + QUOTENAME(@ProcedureName) + N' TO PUBLIC;';
        ELSE IF @PermissionState = 'D'
            SET @PermissionSql = N'DENY EXECUTE ON OBJECT::dbo.' + QUOTENAME(@ProcedureName) + N' TO PUBLIC;';
        ELSE IF @PermissionState = 'W'
            SET @PermissionSql = N'GRANT EXECUTE ON OBJECT::dbo.' + QUOTENAME(@ProcedureName) + N' TO PUBLIC WITH GRANT OPTION;';
        ELSE
            SET @PermissionSql = NULL;
        IF @PermissionSql IS NOT NULL EXEC sys.sp_executesql @PermissionSql;
        FETCH NEXT FROM predecessor_permissions INTO @ProcedureName, @PermissionState;
    END;
    CLOSE predecessor_permissions;
    DEALLOCATE predecessor_permissions;

    IF OBJECT_ID(N'dbo.fn_ResumePublicationUtf8', N'FN') IS NOT NULL
        DROP FUNCTION dbo.fn_ResumePublicationUtf8;

    IF OBJECT_ID(N'dbo.trg_resume_publication_receipts_immutable', N'TR') IS NOT NULL
        DROP TRIGGER dbo.trg_resume_publication_receipts_immutable;
    IF OBJECT_ID(N'dbo.resume_publication_outbox', N'U') IS NOT NULL
        DROP TABLE dbo.resume_publication_outbox;
    IF OBJECT_ID(N'dbo.resume_publication_receipts', N'U') IS NOT NULL
        DROP TABLE dbo.resume_publication_receipts;
    IF OBJECT_ID(N'dbo.resume_publication_evidence', N'U') IS NOT NULL
        DROP TABLE dbo.resume_publication_evidence;
    IF OBJECT_ID(N'dbo.resume_publication_revisions', N'U') IS NOT NULL
        DROP TABLE dbo.resume_publication_revisions;
    IF OBJECT_ID(N'dbo.resume_sharing_state', N'U') IS NOT NULL
        DROP TABLE dbo.resume_sharing_state;
    DROP TABLE dbo.resume_publication_core_execute_permissions;

    DELETE dbo.schema_migrations
    WHERE migration_id = N'PS-RESUME-PUBLICATION-001';

    COMMIT;
END TRY
BEGIN CATCH
    IF @@TRANCOUNT > 0 ROLLBACK;
    THROW;
END CATCH;
