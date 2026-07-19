import pathlib
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[1]
FORWARD = ROOT / "SQL FIles" / "Migrations" / "proposed" / "PS-VOICE-001_voice_capture.sql"
ROLLBACK = ROOT / "SQL FIles" / "Migrations" / "proposed" / "PS-VOICE-001_voice_capture_rollback.sql"
VERIFY = ROOT / "SQL FIles" / "Verification" / "PS-VOICE-001_owner_isolation_verify.sql"


class VoiceMigrationContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.forward = FORWARD.read_text(encoding="utf-8")
        cls.rollback = ROLLBACK.read_text(encoding="utf-8")
        cls.verify = VERIFY.read_text(encoding="utf-8")

    def test_forward_defines_owner_bound_sources_attempts_and_links(self):
        for contract in (
            "dbo.voice_media_sources",
            "dbo.voice_transcription_attempts",
            "dbo.voice_capture_links",
            "source_key",
            "owner_profile_id",
            "row_version",
            "provider_transcript",
            "attempt_number",
        ):
            self.assertIn(contract, self.forward)

    def test_forward_defines_all_explicit_states_and_limits(self):
        for state in (
            "uploading",
            "queued",
            "processing",
            "needs_review",
            "confirmed",
            "failed",
            "deletion_pending",
            "deleted",
        ):
            self.assertIn(state, self.forward)
        self.assertIn("20971520", self.forward)
        self.assertIn("180000", self.forward)
        self.assertIn("en-US", self.forward)

    def test_every_operation_resolves_owner_and_uses_concurrency(self):
        for procedure in (
            "usp_CreateVoiceDraft",
            "usp_QueueVoiceTranscription",
            "usp_MarkVoiceTranscriptionProcessing",
            "usp_CompleteVoiceTranscription",
            "usp_GetVoiceDraftForOwner",
            "usp_GetVoiceMediaForOwner",
            "usp_ConfirmVoiceCapture",
            "usp_BeginVoiceDraftDeletion",
            "usp_FinalizeVoiceDraftDeletion",
            "usp_FinalizeVoiceCaptureDeletion",
        ):
            self.assertIn(procedure, self.forward)
        self.assertGreaterEqual(self.forward.count("@UserKey"), 20)
        self.assertGreaterEqual(self.forward.count("@ExpectedRowVersion"), 7)

    def test_confirmation_is_one_to_one_private_and_pins_attempt(self):
        self.assertIn("UNIQUE", self.forward)
        self.assertIn("visibility", self.forward)
        self.assertIn("'private'", self.forward)
        self.assertIn("successful_attempt_id", self.forward)
        self.assertIn("capture_type", self.forward)
        self.assertIn("'voice'", self.forward)

    def test_retry_atomically_recovers_stranded_queued_and_processing_attempts(self):
        self.assertIn(
            "source.state IN (N''queued'', N''processing'')",
            self.forward,
        )
        self.assertIn("safe_error_code = N''recovery_retry''", self.forward)
        self.assertIn("state IN (N''queued'', N''processing'')", self.forward)
        self.assertIn("@ExpectedRowVersion", self.forward)
        self.assertIn(
            "AND source.row_version = @ExpectedRowVersion",
            self.forward,
        )
        self.assertIn("recovery_retry", self.verify)

    def test_delete_is_pending_then_final_and_preserves_moment_tombstone(self):
        self.assertIn("usp_DeleteCapture", self.forward)
        self.assertIn("deletion_pending", self.forward)
        self.assertIn("usp_FinalizeVoiceCaptureDeletion", self.forward)
        self.assertIn("source_state = N''deleted''", self.forward)
        self.assertIn("capture_id = NULL", self.forward)

    def test_export_distinguishes_provider_and_approved_text_without_blob_url(self):
        self.assertIn("provider_transcript", self.forward)
        self.assertIn("original_body", self.forward)
        self.assertNotIn("blob.core.windows.net", self.forward.lower())

    def test_protected_procedures_are_fingerprinted(self):
        self.assertIn("PS_VOICE_001_DEFINITION_HASH", self.forward)
        self.assertIn("HASHBYTES('SHA2_256'", self.forward)
        self.assertIn("PS_VOICE_001_DEFINITION_HASH", self.rollback)

    def test_rollback_refuses_data_later_migrations_and_drift(self):
        self.assertIn("rollback refused", self.rollback.lower())
        self.assertIn("voice_media_sources", self.rollback)
        self.assertIn("schema_migrations", self.rollback)
        self.assertIn("definition drift", self.rollback.lower())

    def test_verifier_exercises_two_owner_denials_and_outer_rollback(self):
        self.assertIn("BEGIN TRANSACTION", self.verify)
        self.assertIn("ROLLBACK TRANSACTION", self.verify)
        self.assertIn("Voice Owner A", self.verify)
        self.assertIn("Voice Owner B", self.verify)
        self.assertGreaterEqual(self.verify.lower().count("cross-owner"), 8)
        self.assertIn("provider transcript changed", self.verify.lower())
        self.assertIn("downstream", self.verify.lower())


if __name__ == "__main__":
    unittest.main()
