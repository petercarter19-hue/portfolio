/*
 PS-OPPSLATE-USE-001 — Workshop D saved-slate use disclosure read.

 Additive only. One owner-scoped, read-only procedure
 (dbo.usp_GetOpportunitySlateUseForOwner) answering exactly one question for
 exactly one member: "does any version of MY explicitly saved Opportunity
 Slate cite THIS knowledge item?" — plus one supporting nonclustered index on
 dbo.opportunity_saved_evidence so that per-item reverse lookup is a seek,
 not a scan. No table, column, row, or existing procedure changes; no
 Opportunity Slate behavior changes; nothing is written by anything here.

 WHY dbo.opportunity_saved_evidence AND NOT THE ANALYSIS CITATIONS. The
 accepted Workshop D architecture (owner direction 2026-08-25,
 PS-WORKSHOP-USE-DISCLOSURE-001) fixes the single durable authority for
 "actually cited by Opportunity Slate": rows a member explicitly created with
 Save privately. dbo.opportunity_analysis_citations is working data — it
 expires with the working session and is destroyed by purge, session delete,
 re-proposal, statement correction, and re-analysis — so a Workshop label
 over it would flap on a timer the member was never asked to watch. The
 saved snapshot is the record the member chose to keep; any saved version
 counts, not only the latest, because every saved version remains a
 member-kept, reopenable record.

 THE FOURTH F6-COUPLED SITE. This procedure filters
 evidence_kind = N'knowledge_item'. That predicate is deliberately coupled to
 the currency read's knowledge_item branch in
 usp_GetOpportunitySavedSlateForOwner (PS-OPPSLATE-003) and to
 SAVED_EVIDENCE_CURRENCY_KINDS in services/opportunity_slate_service.py. A
 future slice that grounds saved slates on Moments must widen all of them
 together — adding a Moment branch here too, or Moment citations will be
 silently invisible to Workshop's use disclosure.

 No inference about the table's total size is made from the per-save row
 bound: saved versions accumulate across members and time. The index is built
 ONLINE and waits for its required low-priority lock for at most one minute,
 aborting its own operation rather than killing blockers. The disposable gate
 proves that exact operation and rollback on the supported Azure SQL target;
 a production schema apply remains separately authorized and fail-closed.
*/
SET NOCOUNT ON;
SET XACT_ABORT ON;

BEGIN TRY
    BEGIN TRANSACTION;

    IF NOT EXISTS (SELECT 1 FROM dbo.schema_migrations WHERE migration_id = N'PS-OPPSLATE-USE-001')
    BEGIN
        /* CREATE OR ALTER PROCEDURE succeeds under deferred name resolution
           even when the tables it reads are missing, so the prerequisite is
           checked loudly instead of discovered at first member request. */
        IF OBJECT_ID(N'dbo.opportunity_saved_evidence', N'U') IS NULL
           OR OBJECT_ID(N'dbo.opportunity_saved_qualifications', N'U') IS NULL
           OR OBJECT_ID(N'dbo.opportunity_saved_results', N'U') IS NULL
           OR OBJECT_ID(N'dbo.opportunity_slates', N'U') IS NULL
            THROW 56101, 'PS-OPPSLATE-USE-001 requires the PS-OPPSLATE-003 saved-slate tables.', 1;

        /* The reverse-read access path: every signed-in Workshop item
           detail, edit, and delete-confirm render asks about one
           (owner, kind, key) triple. Neither existing index on this table
           leads on the owner or the evidence key. */
        CREATE INDEX IX_opportunity_saved_evidence_owner_use
            ON dbo.opportunity_saved_evidence(owner_profile_id, evidence_kind, evidence_key)
            INCLUDE (opportunity_saved_qualification_id)
            WITH
            (
                ONLINE = ON
                (
                    WAIT_AT_LOW_PRIORITY
                    (
                        MAX_DURATION = 1 MINUTES,
                        ABORT_AFTER_WAIT = SELF
                    )
                )
            );

        EXEC(N'
            CREATE OR ALTER PROCEDURE dbo.usp_GetOpportunitySlateUseForOwner
                @UserKey nvarchar(300),
                @KnowledgeItemKey uniqueidentifier
            AS
            BEGIN
                SET NOCOUNT ON;

                /* Owner resolution happens HERE, from the trusted server
                   identity string, exactly like every other *ForOwner
                   procedure. The caller cannot name a profile. */
                SET @UserKey = NULLIF(LTRIM(RTRIM(@UserKey)), N'''');
                IF @UserKey IS NULL OR @KnowledgeItemKey IS NULL RETURN;

                DECLARE @ProfileId bigint;
                SELECT @ProfileId = profile.profile_id
                FROM dbo.member_profiles AS profile
                JOIN dbo.app_users AS app_user ON app_user.id = profile.user_id
                WHERE app_user.user_key = @UserKey
                  AND app_user.active = 1
                  AND profile.active = 1;
                IF @ProfileId IS NULL RETURN;

                /* One aggregate row when cited; zero rows when not. No
                   bodies, excerpts, employer text, or Opportunity Slate
                   content leave this procedure — counts, a version number,
                   and a timestamp only. The kind filter is the F6-coupled
                   predicate described in the migration header.

                   The owner slate is joined inside this same SELECT so the
                   current save version and cited saved versions are one
                   statement-consistent disclosure. One slate per member is
                   guaranteed by UQ_opportunity_slates_owner; no slate still
                   produces the same zero-row shape as uncited or foreign.

                   Deliberately NOT joined to dbo.knowledge_items: a citation
                   of a since-deleted or archived item is still a real use
                   the member should see named before acting again. */
                SELECT
                    COUNT(DISTINCT saved_result.opportunity_saved_result_id) AS citing_version_count,
                    MAX(saved_result.saved_at_utc) AS latest_saved_at_utc,
                    MAX(saved_result.save_version_number) AS latest_save_version_number,
                    CAST(CASE
                             WHEN MAX(saved_result.save_version_number) = slate.current_save_version_number
                             THEN 1 ELSE 0
                         END AS bit) AS cites_latest_saved_version
                FROM dbo.opportunity_slates AS slate
                JOIN dbo.opportunity_saved_evidence AS saved_evidence
                  ON saved_evidence.owner_profile_id = slate.owner_profile_id
                JOIN dbo.opportunity_saved_qualifications AS saved_qualification
                  ON saved_qualification.opportunity_saved_qualification_id = saved_evidence.opportunity_saved_qualification_id
                 AND saved_qualification.owner_profile_id = saved_evidence.owner_profile_id
                JOIN dbo.opportunity_saved_results AS saved_result
                  ON saved_result.opportunity_saved_result_id = saved_qualification.opportunity_saved_result_id
                 AND saved_result.owner_profile_id = saved_qualification.owner_profile_id
                WHERE saved_evidence.owner_profile_id = @ProfileId
                  AND saved_evidence.evidence_kind = N''knowledge_item''
                  AND saved_evidence.evidence_key = @KnowledgeItemKey
                  AND saved_result.opportunity_slate_id = slate.opportunity_slate_id
                GROUP BY slate.current_save_version_number
                HAVING COUNT(*) > 0;
            END;
        ');

        INSERT dbo.schema_migrations (migration_id, description, application_version)
        VALUES
        (
            N'PS-OPPSLATE-USE-001',
            N'Additive Workshop D saved-slate use disclosure: one owner-scoped read-only procedure (usp_GetOpportunitySlateUseForOwner) and one supporting index on opportunity_saved_evidence. No table, column, row, or existing-procedure change.',
            N'PeerSlate Workshop D use disclosure v1.0'
        );
    END;

    COMMIT TRANSACTION;
END TRY
BEGIN CATCH
    IF XACT_STATE() <> 0 ROLLBACK TRANSACTION;
    THROW;
END CATCH;
