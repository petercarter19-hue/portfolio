"""Reusable, parameterized access to PeerSlate Azure SQL procedures."""

import re

from db import fetch_all_result_sets, get_connection


_PROCEDURE_NAME = re.compile(r"^usp_[A-Za-z0-9_]+$")
_PARAMETER_NAME = re.compile(r"^@[A-Za-z][A-Za-z0-9_]*$")

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
        "usp_PurgeExpiredOpportunityWorkingData",
        "usp_SaveOpportunitySourceForOwner",
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
    }
)


class DatabaseServiceError(RuntimeError):
    """Raised when a database operation cannot be completed safely."""


class DatabaseService:
    """Execute known stored procedures with positional parameter binding."""

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
                cursor = connection.cursor()
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
