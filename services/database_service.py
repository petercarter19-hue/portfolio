"""Reusable, parameterized access to PeerSlate Azure SQL procedures."""

import re

from mssql_python import Connection

from db import SQL_QUERY_TIMEOUT_SECONDS, fetch_all_result_sets, get_connection


_PROCEDURE_NAME = re.compile(r"^usp_[A-Za-z0-9_]+$")
_PARAMETER_NAME = re.compile(r"^@[A-Za-z][A-Za-z0-9_]*$")
_DATABASE_NAME = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_-]{0,127}$")

ALLOWED_PROCEDURES = frozenset(
    {
        "usp_AddSlateItem",
        "usp_ArchiveSlateItem",
        "usp_ArchiveCapture",
        "usp_CompleteChallenge",
        "usp_ConfirmMoment",
        # PS-OPPSLATE-001 (Opportunity Slate, slice OS-1): the ephemeral
        # working-session store. Every one of these is owner-scoped and
        # resolves @UserKey itself.
        "usp_ConfirmOpportunitySourceForOwner",
        "usp_CorrectOpportunitySourceForOwner",
        "usp_DeleteOpportunityWorkingSessionForOwner",
        "usp_GetOpportunityWorkingSessionForOwner",
        # PS-OPPORTUNITY-SLATE-002 R1: the member-reviewed source identity is
        # additive to the existing owner-scoped working session.
        "usp_GetOpportunitySourceIdentityForOwner",
        "usp_PurgeExpiredOpportunityWorkingData",
        "usp_SaveOpportunitySourceForOwner",
        "usp_SaveOpportunitySourceIdentityForOwner",
        # PS-OPPSLATE-001 slice OS-2: AI step 1 and 2 proposals and the
        # member's decisions on them. Same owner-scoping rule — each resolves
        # @UserKey itself and re-asserts owner_profile_id in every predicate.
        "usp_ConfirmOpportunityRequirementsForOwner",
        "usp_CorrectOpportunityRequirementStatementForOwner",
        "usp_GetOpportunityRequirementsForOwner",
        "usp_GetOpportunitySourceReviewForOwner",
        "usp_ResolveOpportunitySourceConcernForOwner",
        "usp_SaveOpportunityRequirementProposalForOwner",
        "usp_SaveOpportunitySourceReviewForOwner",
        # PS-OPPSLATE-001 slice OS-3: the alignment analysis, its grounded
        # citations, the member's own responses, and the READ-ONLY evidence
        # allowlist the analysis is grounded in.
        "usp_GetOpportunityAnalysisForOwner",
        "usp_ListOpportunityEvidenceForOwner",
        "usp_SaveOpportunityAnalysisForOwner",
        "usp_SaveOpportunityResponseForOwner",
        # PS-OPPSLATE-001 slice OS-4: the durable saved slate — the first
        # Opportunity Slate record that outlives the working session it was
        # computed from. Same owner-scoping rule, and the save procedure
        # additionally builds its snapshot from the owner's own rows rather
        # than from any payload.
        "usp_DeleteOpportunitySavedSlateForOwner",
        "usp_GetOpportunitySavedSlateForOwner",
        "usp_SaveOpportunitySlateForOwner",
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
        "usp_GetMomentForOwner",
        "usp_GetOwnerHomeForOwner",
        "usp_GetPeerSlateUserDashboard",
        "usp_ArchiveKnowledgeItemForOwner",
        # PS-WORKSHOP-002 (leg 9): the gated in-place knowledge backlog
        # confirmation. Draft/gate not yet applied anywhere (registry.json
        # gate is null); allowlisted ahead of the apply, degrade-safe --
        # see workshop_routes.py and opportunity_slate_routes.py.
        "usp_ConfirmAuthoredKnowledgeBacklogForOwner",
        "usp_DeleteKnowledgeItemForOwner",
        "usp_ListCapturesForOwner",
        "usp_ListKnowledgeItemsForOwner",
        "usp_ListMomentPlacementsForOwner",
        "usp_GetOwnerLivingResume",
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
        # PS-ASK-PETE-DIRECT-001: the private recruiter question inbox.
        # Draft/gate not yet applied anywhere (registry.json gate is null),
        # and the blueprint that calls these is not registered in app.py, so
        # nothing reaches them today.
        # Anonymous-capable write; requires consent and resolves the RECIPIENT
        # key it is given. It is the only procedure here whose caller is not
        # the owner, and it returns an outcome word and nothing else.
        "usp_SubmitRecruiterQuestion",
        # Owner-scoped bounded read of that recipient's own questions.
        "usp_ListRecruiterQuestionsForOwner",
        # Owner-scoped, version-fenced new/read/archived change. Archive-only:
        # there is deliberately no delete or purge procedure to allowlist.
        "usp_SetRecruiterQuestionStatusForOwner",
        # PS-COMMUNITY-RETENTION-001 and PS-COMMUNITY-RESTORE-001. Omitting a
        # procedure here does not merely disable it: execute_procedure raises
        # ValueError before the database boundary. The retired request-path
        # scheduler turned that omission into a site-wide outage. Maintenance
        # is now out of process, but the allowlist remains fail closed.
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
)


class DatabaseServiceError(RuntimeError):
    """Raised when a database operation cannot be completed safely."""


class DatabaseService:
    """Execute known stored procedures with positional parameter binding."""

    @staticmethod
    def _cursor(connection):
        """Create one cursor and prove the pinned driver carried the bound.

        mssql-python 1.11's public ``Connection.cursor`` constructs
        ``Cursor(connection, timeout=connection.timeout)``. The defensive
        checks below turn a future driver-contract change into a closed
        dependency failure instead of silently restoring unbounded queries.
        """

        real_driver_connection = isinstance(connection, Connection)
        if (
            real_driver_connection
            and getattr(connection, "timeout", None) != SQL_QUERY_TIMEOUT_SECONDS
        ):
            raise DatabaseServiceError("Database query timeout is unavailable.")
        cursor = connection.cursor()
        if (
            real_driver_connection
            and getattr(cursor, "_timeout", None) != SQL_QUERY_TIMEOUT_SECONDS
        ):
            try:
                cursor.close()
            except Exception:
                pass
            raise DatabaseServiceError("Database query timeout is unavailable.")
        return cursor

    def assert_database_target(self, expected_database):
        """Fail closed unless the connection reaches the exact database."""

        if (
            not isinstance(expected_database, str)
            or not _DATABASE_NAME.fullmatch(expected_database)
        ):
            raise ValueError("Invalid expected database name.")
        try:
            with get_connection() as connection:
                cursor = self._cursor(connection)
                cursor.execute("SELECT DB_NAME() AS database_name;")
                rows = fetch_all_result_sets(cursor)
        except DatabaseServiceError:
            raise
        except Exception as error:
            raise DatabaseServiceError("Database target check failed.") from error
        actual = rows[0][0].get("database_name") if rows and rows[0] else None
        if actual != expected_database:
            raise DatabaseServiceError("Database target check failed.")
        return True

    def execute_procedure(self, procedure_name, parameters=None):
        if (
            not _PROCEDURE_NAME.fullmatch(procedure_name)
            or procedure_name not in ALLOWED_PROCEDURES
        ):
            raise ValueError("Invalid stored procedure name.")

        bound_parameters = list(parameters or [])
        assignments = []
        values = []

        for parameter_name, value in bound_parameters:
            if not _PARAMETER_NAME.fullmatch(parameter_name):
                raise ValueError("Invalid stored procedure parameter name.")

            assignments.append(f"{parameter_name} = ?")
            values.append(value)

        statement = f"EXEC dbo.{procedure_name}"
        if assignments:
            statement = f"{statement} {', '.join(assignments)}"

        try:
            with get_connection() as connection:
                cursor = self._cursor(connection)
                if values:
                    cursor.execute(statement, tuple(values))
                else:
                    cursor.execute(statement)
                return fetch_all_result_sets(cursor)
        except Exception as error:
            raise DatabaseServiceError(
                f"Database procedure {procedure_name} failed."
            ) from error

    def first_result(self, procedure_name, parameters=None):
        result_sets = self.execute_procedure(procedure_name, parameters)
        return result_sets[0] if result_sets else []

    def first_row(self, procedure_name, parameters=None):
        rows = self.first_result(procedure_name, parameters)
        return rows[0] if rows else None

    def last_result(self, procedure_name, parameters=None):
        result_sets = self.execute_procedure(procedure_name, parameters)
        return result_sets[-1] if result_sets else []

    def last_row(self, procedure_name, parameters=None):
        rows = self.last_result(procedure_name, parameters)
        return rows[0] if rows else None

    @staticmethod
    def name_result_sets(result_sets, names):
        result_names = list(names)
        return {
            name: result_sets[index] if index < len(result_sets) else []
            for index, name in enumerate(result_names)
        }


database_service = DatabaseService()
