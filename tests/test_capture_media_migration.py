import pathlib
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[1]
FORWARD = (
    ROOT
    / "SQL FIles"
    / "Migrations"
    / "proposed"
    / "PS-CAPTURE-MEDIA-001_photo_sources.sql"
)
ROLLBACK = (
    ROOT
    / "SQL FIles"
    / "Migrations"
    / "proposed"
    / "PS-CAPTURE-MEDIA-001_photo_sources_rollback.sql"
)
VERIFY = (
    ROOT
    / "SQL FIles"
    / "Verification"
    / "PS-CAPTURE-MEDIA-001_owner_isolation_verify.sql"
)


class CaptureMediaMigrationContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.forward = FORWARD.read_text(encoding="utf-8")
        cls.rollback = ROLLBACK.read_text(encoding="utf-8")
        cls.verify = VERIFY.read_text(encoding="utf-8")

    def test_defines_generic_owner_bound_sources_and_links(self):
        for contract in (
            "dbo.capture_media_sources",
            "dbo.capture_media_links",
            "source_type",
            "source_key",
            "owner_profile_id",
            "row_version",
            "original_sha256_digest",
            "derivative_sha256_digest",
            "scan_result",
        ):
            self.assertIn(contract, self.forward)
        self.assertIn("FOREIGN KEY (source_id, owner_profile_id)", self.forward)
        self.assertIn("FOREIGN KEY (capture_id, owner_profile_id)", self.forward)

    def test_defines_photo_limits_states_and_draft_cap(self):
        for state in (
            "uploading",
            "scanning",
            "processing",
            "needs_review",
            "confirmed",
            "failed",
            "rejected",
            "deletion_pending",
            "deleted",
        ):
            self.assertIn(state, self.forward)
        for limit in ("10485760", "2400", ">= 10"):
            self.assertIn(limit, self.forward)
        self.assertIn("image/jpeg", self.forward)
        self.assertIn("image/png", self.forward)

    def test_owner_resolving_procedures_cover_full_lifecycle(self):
        for procedure in (
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
        ):
            self.assertIn(procedure, self.forward)
        self.assertGreaterEqual(self.forward.count("@UserKey"), 25)
        self.assertGreaterEqual(self.forward.count("@ExpectedRowVersion"), 10)

    def test_scan_is_fail_closed_and_confirmation_is_private(self):
        self.assertIn("N''unknown''", self.forward)
        self.assertIn("N''malicious'' THEN N''rejected''", self.forward)
        self.assertIn("source.scan_result = N''clean''", self.forward)
        self.assertIn("N''photo'', @ApprovedBody, N''private''", self.forward)
        self.assertIn("UQ_capture_media_links_source", self.forward)
        self.assertIn("UQ_capture_media_links_capture", self.forward)

    def test_shared_delete_and_export_preserve_voice_and_add_photo(self):
        self.assertIn("CREATE OR ALTER PROCEDURE dbo.usp_DeleteCapture", self.forward)
        self.assertIn("N''voice'' AS source_type", self.forward)
        self.assertIn("N''photo'' AS source_type", self.forward)
        self.assertIn("blob_name", self.forward)
        self.assertIn("original_blob_name", self.forward)
        self.assertIn("derivative_blob_name", self.forward)
        self.assertIn("provider_transcript", self.forward)
        self.assertNotIn("blob.core.windows.net", self.forward.lower())

    def test_procedures_are_fingerprinted_and_rollback_is_guarded(self):
        self.assertIn("PS_CAPTURE_MEDIA_001_DEFINITION_HASH", self.forward)
        self.assertIn("HASHBYTES('SHA2_256'", self.forward)
        self.assertIn("PS_CAPTURE_MEDIA_001_DEFINITION_HASH", self.rollback)
        self.assertIn("rollback refused", self.rollback.lower())
        self.assertIn("definition drift", self.rollback.lower())
        self.assertIn("a later migration is present", self.rollback)
        self.assertIn("PS_VOICE_001_DEFINITION_HASH", self.rollback)
        self.assertIn("CREATE OR ALTER PROCEDURE dbo.usp_DeleteCapture", self.rollback)
        self.assertIn("CREATE OR ALTER PROCEDURE dbo.usp_ExportCaptureForOwner", self.rollback)

    def test_verifier_uses_two_owners_outer_rollback_and_no_downstream(self):
        self.assertIn("BEGIN TRANSACTION", self.verify)
        self.assertIn("ROLLBACK TRANSACTION", self.verify)
        self.assertIn("Photo Owner A", self.verify)
        self.assertIn("Photo Owner B", self.verify)
        self.assertGreaterEqual(self.verify.lower().count("cross-owner"), 8)
        self.assertIn("malicious", self.verify.lower())
        self.assertIn("downstream", self.verify.lower())


if __name__ == "__main__":
    unittest.main()
