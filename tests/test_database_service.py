import unittest
from unittest.mock import MagicMock, call, patch

from mssql_python import DatabaseError

from services.connection_foundation_repository import CONNECTION_FOUNDATION_PROCEDURES
from services.database_service import (
    ALLOWED_PROCEDURES,
    DatabaseService,
    DatabaseServiceError,
)


class DatabaseServiceTests(unittest.TestCase):
    def setUp(self):
        self.service = DatabaseService()

    def test_rejects_untrusted_procedure_name(self):
        with self.assertRaises(ValueError):
            self.service.execute_procedure("usp_Good; DROP TABLE users")

    def test_rejects_unknown_well_formed_procedure_name(self):
        with self.assertRaises(ValueError):
            self.service.execute_procedure("usp_UnexpectedProcedure")

    def test_rejects_untrusted_parameter_name(self):
        with self.assertRaises(ValueError):
            self.service.execute_procedure(
                "usp_Good", [("@UserKey; DELETE", "test-user-1")]
            )

    def test_names_result_sets_and_fills_missing_sections(self):
        result = self.service.name_result_sets([[{"id": 1}]], ("first", "second"))

        self.assertEqual(result["first"], [{"id": 1}])
        self.assertEqual(result["second"], [])

    def test_database_target_rejects_an_invalid_name_without_connecting(self):
        with patch("services.database_service.get_connection") as connection:
            with self.assertRaises(ValueError):
                self.service.assert_database_target("prod]; DROP DATABASE prod")
        connection.assert_not_called()

    @patch("services.database_service.get_connection")
    def test_database_target_mismatch_fails_closed(self, get_connection):
        connection = MagicMock()
        cursor = connection.__enter__.return_value.cursor.return_value
        cursor.description = [("database_name",)]
        cursor.fetchall.return_value = [("unexpected",)]
        cursor.nextset.return_value = False
        get_connection.return_value = connection

        with self.assertRaises(DatabaseServiceError):
            self.service.assert_database_target("peerslate-database")

        cursor.execute.assert_called_once_with("SELECT DB_NAME() AS database_name;")

    def test_last_result_selects_final_procedure_output(self):
        self.service.execute_procedure = lambda *args, **kwargs: [
            [{"helper": True}],
            [{"saved_id": 42}],
        ]

        result = self.service.last_result("usp_AddSlateItem")

        self.assertEqual(result, [{"saved_id": 42}])

    @patch("services.database_service.get_connection")
    def test_driver_error_during_procedure_is_not_retried(self, get_connection):
        connection = MagicMock()
        cursor = connection.__enter__.return_value.cursor.return_value
        cursor.execute.side_effect = DatabaseError(
            "test driver error", "test database error"
        )
        get_connection.return_value = connection

        with self.assertRaises(DatabaseServiceError):
            self.service.execute_procedure(
                "usp_UpsertAppUserFromAuth",
                [("@AuthProvider", "aad")],
            )

        get_connection.assert_called_once_with()
        cursor.execute.assert_called_once()

    def test_capture_lifecycle_procedures_are_explicitly_allowlisted(self):
        expected = {
            "usp_GetCaptureForOwner",
            "usp_CorrectCapture",
            "usp_ArchiveCapture",
            "usp_RestoreCapture",
            "usp_DeleteCapture",
            "usp_ExportCaptureForOwner",
        }

        self.assertTrue(expected.issubset(ALLOWED_PROCEDURES))

    def test_moment_procedures_are_explicitly_allowlisted(self):
        expected = {
            "usp_CreateOrReopenMomentProposal",
            "usp_GetMomentForOwner",
            "usp_SaveMomentProposal",
            "usp_ConfirmMoment",
            "usp_DiscardMomentProposal",
        }

        self.assertTrue(expected.issubset(ALLOWED_PROCEDURES))

    def test_placement_procedures_are_explicitly_allowlisted(self):
        expected = {
            "usp_CreateOrReactivateMomentPlacement",
            "usp_ListMomentPlacementsForOwner",
            "usp_RemoveMomentPlacement",
        }

        self.assertTrue(expected.issubset(ALLOWED_PROCEDURES))

    def test_voice_procedures_are_explicitly_allowlisted(self):
        expected = {
            "usp_CreateVoiceDraft",
            "usp_FailVoiceUpload",
            "usp_QueueVoiceTranscription",
            "usp_MarkVoiceTranscriptionProcessing",
            "usp_CompleteVoiceTranscription",
            "usp_FailVoiceTranscription",
            "usp_GetVoiceDraftForOwner",
            "usp_GetVoiceMediaForOwner",
            "usp_ConfirmVoiceCapture",
            "usp_BeginVoiceDraftDeletion",
            "usp_FinalizeVoiceDraftDeletion",
            "usp_FinalizeVoiceCaptureDeletion",
        }

        self.assertTrue(expected.issubset(ALLOWED_PROCEDURES))

    def test_connection_foundation_allowlist_is_the_exact_repository_contract(self):
        expected = {
            "usp_CommitConnectionRelationshipCommandForActor",
            "usp_GetConnectionRelationshipCommandForActor",
            "usp_GetConnectionRelationshipSnapshotForActor",
        }

        self.assertEqual(CONNECTION_FOUNDATION_PROCEDURES, frozenset(expected))
        self.assertEqual(expected & set(ALLOWED_PROCEDURES), expected)
        self.assertEqual(
            {
                name
                for name in ALLOWED_PROCEDURES
                if "ConnectionRelationship" in name
            },
            expected,
        )

    @patch("services.database_service.get_connection")
    def test_connection_foundation_calls_bind_every_value(self, get_connection):
        connection = MagicMock()
        cursor = connection.__enter__.return_value.cursor.return_value
        cursor.description = None
        cursor.nextset.return_value = False
        get_connection.return_value = connection
        digest = "a" * 64
        cases = (
            (
                "usp_CommitConnectionRelationshipCommandForActor",
                (
                    ("@ActorUserKey", "actorAlpha_001"),
                    ("@SubjectUserKey", "subject-id-11111111"),
                    ("@Command", "request"),
                    ("@ExpectedRelationshipVersion", None),
                    ("@IdempotencyKey", "request-0001"),
                    ("@RequestDigest", digest),
                ),
            ),
            (
                "usp_GetConnectionRelationshipCommandForActor",
                (
                    ("@ActorUserKey", "actorAlpha_001"),
                    ("@IdempotencyKey", "request-0001"),
                ),
            ),
            (
                "usp_GetConnectionRelationshipSnapshotForActor",
                (
                    ("@ActorUserKey", "actorAlpha_001"),
                    ("@SubjectUserKey", "subject-id-11111111"),
                ),
            ),
        )

        for procedure_name, parameters in cases:
            self.service.execute_procedure(procedure_name, parameters)

        self.assertEqual(
            cursor.execute.call_args_list,
            [
                call(
                    "EXEC dbo.usp_CommitConnectionRelationshipCommandForActor "
                    "@ActorUserKey = ?, @SubjectUserKey = ?, @Command = ?, "
                    "@ExpectedRelationshipVersion = ?, @IdempotencyKey = ?, "
                    "@RequestDigest = ?",
                    (
                        "actorAlpha_001",
                        "subject-id-11111111",
                        "request",
                        None,
                        "request-0001",
                        digest,
                    ),
                ),
                call(
                    "EXEC dbo.usp_GetConnectionRelationshipCommandForActor "
                    "@ActorUserKey = ?, @IdempotencyKey = ?",
                    ("actorAlpha_001", "request-0001"),
                ),
                call(
                    "EXEC dbo.usp_GetConnectionRelationshipSnapshotForActor "
                    "@ActorUserKey = ?, @SubjectUserKey = ?",
                    ("actorAlpha_001", "subject-id-11111111"),
                ),
            ],
        )

    @patch("services.database_service.get_connection")
    def test_connection_foundation_typos_and_parameter_fragments_never_connect(
        self, get_connection
    ):
        for procedure_name in (
            "usp_CommitConnectionRelationshipCommandForActors",
            "usp_GetConnectionRelationshipSnapshotForactor",
            "usp_GetConnectionRelationshipForActor",
            "usp_GetConnectionRelationshipCommandForActor;SELECT",
        ):
            with self.subTest(procedure_name=procedure_name):
                with self.assertRaises(ValueError):
                    self.service.execute_procedure(procedure_name)

        with self.assertRaises(ValueError):
            self.service.execute_procedure(
                "usp_GetConnectionRelationshipSnapshotForActor",
                (("@ActorUserKey;SELECT", "actorAlpha_001"),),
            )
        get_connection.assert_not_called()

    def test_the_allowlist_is_exactly_this_set_and_nothing_more(self):
        """2026-08-05 independent review, finding F-5. Every other test in
        this module (and in test_owner_capture.py, test_owner_moment.py,
        test_community_retention_wiring.py) asserts a SUBSET is present. A
        subset check cannot catch a rogue addition — a name injected into
        ALLOWED_PROCEDURES that no test names passes the entire suite,
        because nothing anywhere asserts the upper bound. This is that
        assertion: the full set, exactly, grouped and commented the same way
        the allowlist itself is, so an addition here and an addition there
        are one visible diff apart rather than silently able to drift.

        Failing this test means ALLOWED_PROCEDURES changed. That is not
        automatically wrong — deliberately allowlisting a new procedure is
        normal — but it must never happen without a matching, reviewed
        change to the literal set below.
        """
        base = {
            "usp_AddSlateItem",
            "usp_ArchiveSlateItem",
            "usp_ArchiveCapture",
            "usp_CompleteChallenge",
            "usp_ConfirmMoment",
        }
        # PS-OPPSLATE-001 slice OS-1: the ephemeral working-session store.
        oppslate_os1 = {
            "usp_ConfirmOpportunitySourceForOwner",
            "usp_CorrectOpportunitySourceForOwner",
            "usp_DeleteOpportunityWorkingSessionForOwner",
            "usp_GetOpportunityWorkingSessionForOwner",
            "usp_PurgeExpiredOpportunityWorkingData",
            "usp_SaveOpportunitySourceForOwner",
        }
        # PS-OPPSLATE-001 slice OS-2: AI step 1 and 2 proposals.
        oppslate_os2 = {
            "usp_ConfirmOpportunityRequirementsForOwner",
            "usp_CorrectOpportunityRequirementStatementForOwner",
            "usp_GetOpportunityRequirementsForOwner",
            "usp_GetOpportunitySourceReviewForOwner",
            "usp_ResolveOpportunitySourceConcernForOwner",
            "usp_SaveOpportunityRequirementProposalForOwner",
            "usp_SaveOpportunitySourceReviewForOwner",
        }
        # PS-OPPSLATE-001 slice OS-3: the grounded alignment analysis.
        oppslate_os3 = {
            "usp_GetOpportunityAnalysisForOwner",
            "usp_ListOpportunityEvidenceForOwner",
            "usp_SaveOpportunityAnalysisForOwner",
            "usp_SaveOpportunityResponseForOwner",
        }
        # PS-OPPSLATE-001 slice OS-4: the durable saved slate. Schema
        # PS-OPPSLATE-003 is gated but not yet applied anywhere; these three
        # names are allowlisted at the application layer ahead of that apply
        # (see the OS-4 application-port branch's completion record).
        oppslate_os4 = {
            "usp_DeleteOpportunitySavedSlateForOwner",
            "usp_GetOpportunitySavedSlateForOwner",
            "usp_SaveOpportunitySlateForOwner",
        }
        # PS-OPPORTUNITY-SLATE-002 R1: member-reviewed identity for the
        # signed-in replacement's existing owner-scoped working session.
        oppslate_r1 = {
            "usp_GetOpportunitySourceIdentityForOwner",
            "usp_SaveOpportunitySourceIdentityForOwner",
        }
        # PS-WORKSHOP-USE-DISCLOSURE-001 (Workshop D): the owner-scoped
        # saved-slate use disclosure read over the OS-4 snapshot. Schema
        # PS-OPPSLATE-USE-001 is registered with a disposable-database gate
        # proof but is not applied by this package; the one name is
        # allowlisted at the application layer ahead of any separately
        # authorized apply, degrade-safe (workshop_routes.py's
        # _slate_use_state renders omission or an explicit could-not-check
        # sentence on failure, never a definite negative).
        oppslate_use = {
            "usp_GetOpportunitySlateUseForOwner",
        }
        # Capture, Moment, Placement, Voice, Photo, Journal, Board, Slate
        # Space, Challenges, and account bootstrap — everything else the
        # non-Community, non-Opportunity-Slate product surface calls.
        general = {
            "usp_CorrectCapture",
            "usp_CreateCapture",
            "usp_CreateVoiceDraft",
            "usp_CreateOrReactivateMomentPlacement",
            "usp_CreateOrReopenMomentProposal",
            "usp_DeleteCapture",
            "usp_FailVoiceTranscription",
            "usp_FailVoiceUpload",
            "usp_DiscardMomentProposal",
            "usp_EvaluateUserFlatAchievements",
            "usp_ExportCaptureForOwner",
            "usp_GetCaptureForOwner",
            "usp_GetVoiceDraftForOwner",
            "usp_GetVoiceMediaForOwner",
            "usp_GetKnowledgeItemForOwner",
            "usp_ListKnowledgeItemVersionsForOwner",
            "usp_GetMomentForOwner",
            "usp_GetOwnerHomeForOwner",
            "usp_GetPeerSlateUserDashboard",
            "usp_ArchiveKnowledgeItemForOwner",
            # PS-WORKSHOP-002 (leg 9): the gated in-place knowledge backlog
            # confirmation. Draft/gate not yet applied anywhere; allowlisted
            # ahead of the apply, degrade-safe.
            "usp_ConfirmAuthoredKnowledgeBacklogForOwner",
            "usp_DeleteKnowledgeItemForOwner",
            "usp_ListCapturesForOwner",
            "usp_ListKnowledgeItemsForOwner",
            "usp_ListMomentPlacementsForOwner",
            "usp_CommitLivingResumeCommandForOwner",
            "usp_GetOwnerLivingResume",
            "usp_GetOwnerLivingResumeEditor",
            "usp_GetPublicLivingResumeBySlug",
            "usp_GetSlateSpaceForUser",
            "usp_GetTodayBreakFeedForUser",
            "usp_GetTodayBreakPollOptions",
            "usp_GetTodayJournalPromptForUser",
            "usp_GetUserBadges",
            "usp_GetUserBoardContents",
            "usp_GetUserChallengeHistory",
            "usp_GetUserChallengeProgress",
            "usp_GetUserJournalHistory",
            "usp_LinkSlateItems",
            "usp_ListJournalMomentsForOwner",
            "usp_RecordFeedInteraction",
            "usp_RemoveMomentPlacement",
            "usp_RestoreCapture",
            "usp_RestoreKnowledgeItemForOwner",
            "usp_RestoreSlateItem",
            "usp_QueueVoiceTranscription",
            "usp_MarkVoiceTranscriptionProcessing",
            "usp_CompleteVoiceTranscription",
            "usp_ConfirmVoiceCapture",
            "usp_BeginPhotoDraftDeletion",
            "usp_BeginVoiceDraftDeletion",
            "usp_CompletePhotoProcessing",
            "usp_ConfirmPhotoCapture",
            "usp_CreatePhotoSource",
            "usp_FailPhotoSource",
            "usp_FinalizePhotoCaptureDeletion",
            "usp_FinalizePhotoDraftDeletion",
            "usp_FinalizeVoiceDraftDeletion",
            "usp_FinalizeVoiceCaptureDeletion",
            "usp_GetPhotoMediaForOwner",
            "usp_GetPhotoProcessingSourceForOwner",
            "usp_GetPhotoSourceForOwner",
            "usp_MarkPhotoUploaded",
            "usp_RecordPhotoScanResult",
            "usp_SaveContentToBoard",
            "usp_SaveKnowledgeItemForOwner",
            "usp_SaveMomentForOwner",
            "usp_SaveMomentProposal",
            "usp_SaveJournalResponse",
            "usp_SearchJournalMomentsForOwner",
            "usp_SubmitPollVote",
            "usp_UnlinkSlateItems",
            "usp_UnsaveContentFromBoard",
            "usp_UpdateKnowledgeItemForOwner",
            "usp_UpdateSlateItem",
            "usp_UpsertAppUserFromAuth",
        }
        # PS-COMMUNITY-RETENTION-001 and PS-COMMUNITY-RESTORE-001.
        community = {
            "usp_PurgeCommunityContent",
            "usp_PurgeCommunityAuditEvents",
            "usp_PurgeCommunityOutbox",
            "usp_SetCommunityLegalHold",
            "usp_ListRestorableCommunityForOwner",
            "usp_RestorePublicCommunityPost",
            "usp_RestorePublicCommunityContribution",
            "usp_ListPublicCommunityFeed",
            "usp_ListPublicCommunityShelf",
            "usp_GetPublicCommunityPost",
            "usp_GetPublicCommunityContribution",
            "usp_SearchPublicCommunity",
            "usp_PublishPublicCommunityPost",
            "usp_EditPublicCommunityPost",
            "usp_DeletePublicCommunityPost",
            "usp_AddPublicCommunityContribution",
            "usp_EditPublicCommunityContribution",
            "usp_DeletePublicCommunityContribution",
            "usp_SetPublicCommunityResponse",
            "usp_RemovePublicCommunityResponse",
            "usp_SetPublicCommunitySave",
            "usp_SetPublicCommunityContributionSave",
            "usp_ReservePublicCommunityMedia",
            "usp_MarkPublicCommunityMediaUploaded",
            "usp_GetPublicCommunityMediaForOwner",
            "usp_CompletePublicCommunityMedia",
            "usp_CompensatePublicCommunityMediaCompletion",
            "usp_RejectPublicCommunityMedia",
            "usp_ClaimPublicCommunityMediaCleanup",
            "usp_ClaimPublicCommunityMediaCleanupForOwner",
            "usp_CompletePublicCommunityMediaCleanup",
            "usp_GetPublicCommunityMedia",
            "usp_DeletePublicCommunityMedia",
        }
        # PS-ASK-PETE-DIRECT-001: the private recruiter question inbox. One
        # anonymous-capable consent-required write and two owner-scoped
        # reads/status changes. Archive-only, so there is deliberately no
        # delete or purge procedure in this group — see
        # test_no_recruiter_question_delete_or_purge_is_allowlisted in
        # tests/ask_pete_direct/test_service.py, which asserts that upper
        # bound independently of this literal.
        ask_pete_direct = {
            "usp_SubmitRecruiterQuestion",
            "usp_ListRecruiterQuestionsForOwner",
            "usp_SetRecruiterQuestionStatusForOwner",
        }
        # PS-INTERVIEW-AI-EXTRACT-001: the content-free server_call append.
        # Append only — the 90-day purge procedure
        # (usp_PurgeInterviewAIServerCalls) is deliberately absent because
        # it belongs to the separately named Interview maintenance identity,
        # never the application;
        # tests/test_interview_ai_dark_telemetry_infrastructure.py asserts
        # that absence independently of this literal.
        interview_ai_telemetry = {
            "usp_AppendInterviewAIServerCall",
        }
        # PS-SETTINGS-ACCOUNT-EXPORT-EXPERIENCE-001 (C3). ONLY the three
        # member-facing procedures. Each resolves @UserKey to the active
        # profile itself and filters every row by it. The five worker
        # procedures (Claim/Complete/Fail/Expire/Cleanup) must NEVER appear
        # here: they take no @UserKey and operate system-wide across owners,
        # so allowlisting one would let a browser request act on every
        # member's export at once.
        account_export = {
            "usp_GetAccountExportDownloadMetadataForOwner",
            "usp_GetAccountExportStatusForOwner",
            "usp_RequestAccountExportForOwner",
        }
        # PS-PROFILE-CONNECTIONS-PROVIDER-INTEGRATION-001 (Profile D3): the
        # exact closed PS-CONNECT-002 repository procedure contract.
        connection_foundation = {
            "usp_CommitConnectionRelationshipCommandForActor",
            "usp_GetConnectionRelationshipCommandForActor",
            "usp_GetConnectionRelationshipSnapshotForActor",
        }
        # PS-MVP1-RESUME-EDITOR-001: owner-scoped entry-policy browser
        # procedures plus Resume draft get/commit. Worker expiry sweep stays
        # off this exact set.
        entry_policy = {
            "usp_CommitEntryPolicyCommandForOwner",
            "usp_GetEntryPolicyEntryForOwner",
            "usp_ListEntryPolicyEntriesForOwner",
        }
        resume_draft = {
            "usp_CommitResumeDraftCommandForOwner",
            "usp_GetResumeDraftForOwner",
        }
        # PS-MVP1-INTAKE-GUIDE-001: the owner-scoped composer. Worker job and
        # source-sweep procedures stay off this exact set.
        resume_intake = {
            "usp_GetResumeIntakeWorkspaceForOwner",
            "usp_CommitResumeIntakeSubmissionForOwner",
            "usp_ClaimResumeIntakeRecordingForOwner",
            "usp_CommitResumeIntakeRecordingForOwner",
            "usp_CommitResumeIntakeProposalDecisionForOwner",
            "usp_SetResumeGuideStatusForOwner",
            "usp_PurgeResumeIntakeSourceForOwner",
        }
        # PS-MVP1-MEDIA-INTEGRATION-001: the two owner-scoped private Resume
        # media procedures. They fence the same Resume draft version the draft
        # commands use. Publication, worker, catalog-write and storage
        # procedures stay off this exact set, and allowlisting does not apply
        # the proposed PS-RESUME-MEDIA-001 schema.
        resume_media = {
            "usp_GetResumeMediaDraftForOwner",
            "usp_CommitResumeMediaCommandForOwner",
        }
        # PS-MVP1-PUBLICATION-INTEGRATION-001: complete publication command,
        # readers and catalog fence. Internal helpers stay off this exact set,
        # and allowlisting does not apply proposed schema.
        resume_publication = {
            "usp_CommitResumePublicationCommandForOwner",
            "usp_GetResumePublicationForOwner",
            "usp_GetProfileOwnerBySlug",
            "usp_GetProfileDraftForOwner",
            "usp_SaveProfileDraftForOwner",
            "usp_GetCurrentProfilePublicationForOwner",
            "usp_CommitProfilePublicationForOwner",
            "usp_GetProfilePublicationCommandForOwner",
            "usp_GetResumePublicationReceiptForOwner",
            "usp_ListResumePublicationPolicyForOwner",
            "usp_GetPublicResumePublicationBySlug",
            "usp_GetResumePublicationMediaAuthorization",
            "usp_GetResumeCatalogAsset",
            "usp_CommitResumeCatalogCommandForOwner",
        }
        visitor_ai = {"usp_GetMemberVisitorAiBySlug", "usp_GetMemberVisitorAiPreviewForOwner"}
        expected = (
            base
            | oppslate_os1
            | oppslate_os2
            | oppslate_os3
            | oppslate_os4
            | oppslate_r1
            | oppslate_use
            | general
            | ask_pete_direct
            | community
            | interview_ai_telemetry
            | account_export
            | connection_foundation
            | entry_policy
            | resume_draft
            | resume_intake
            | resume_media
            | resume_publication
            | visitor_ai
        )
        # The groups above must not overlap each other — a name counted
        # twice would silently shrink the real union below the true count
        # and make this test weaker than it looks.
        groups = (
            base,
            oppslate_os1,
            oppslate_os2,
            oppslate_os3,
            oppslate_os4,
            oppslate_r1,
            oppslate_use,
            general,
            ask_pete_direct,
            community,
            interview_ai_telemetry,
            account_export,
            connection_foundation,
            entry_policy,
            resume_draft,
            resume_intake,
            resume_media,
            resume_publication,
            visitor_ai,
        )
        self.assertEqual(sum(len(group) for group in groups), len(expected))
        self.assertEqual(len(expected), 177)
        self.assertEqual(set(ALLOWED_PROCEDURES), expected)

    def test_visitor_ai_internal_helper_is_not_browser_executable(self):
        with patch("services.database_service.get_connection") as connection:
            with self.assertRaises(ValueError):
                self.service.execute_procedure("usp_MemberVisitorAiSnapshotInternal", [("@OwnerPreview", True)])
        connection.assert_not_called()

    def test_living_resume_editor_procedures_are_exactly_allowlisted(self):
        expected = {
            "usp_CommitLivingResumeCommandForOwner",
            "usp_GetOwnerLivingResumeEditor",
        }

        self.assertTrue(expected.issubset(ALLOWED_PROCEDURES))
        self.assertEqual(
            {
                name
                for name in ALLOWED_PROCEDURES
                if "LivingResume" in name and name not in {
                    "usp_GetOwnerLivingResume",
                    "usp_GetPublicLivingResumeBySlug",
                }
            },
            expected,
        )

    def test_photo_procedures_are_explicitly_allowlisted(self):
        expected = {
            "usp_CreatePhotoSource",
            "usp_MarkPhotoUploaded",
            "usp_FailPhotoSource",
            "usp_GetPhotoSourceForOwner",
            "usp_GetPhotoProcessingSourceForOwner",
            "usp_RecordPhotoScanResult",
            "usp_CompletePhotoProcessing",
            "usp_ConfirmPhotoCapture",
            "usp_GetPhotoMediaForOwner",
            "usp_BeginPhotoDraftDeletion",
            "usp_FinalizePhotoDraftDeletion",
            "usp_FinalizePhotoCaptureDeletion",
        }

        self.assertTrue(expected.issubset(ALLOWED_PROCEDURES))


if __name__ == "__main__":
    unittest.main()
