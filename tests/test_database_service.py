import unittest

from services.database_service import ALLOWED_PROCEDURES, DatabaseService


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

    def test_last_result_selects_final_procedure_output(self):
        self.service.execute_procedure = lambda *args, **kwargs: [
            [{"helper": True}],
            [{"saved_id": 42}],
        ]

        result = self.service.last_result("usp_AddSlateItem")

        self.assertEqual(result, [{"saved_id": 42}])

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


if __name__ == "__main__":
    unittest.main()
