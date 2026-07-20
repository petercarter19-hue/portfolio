import pathlib
import unittest


SCRIPT = (
    pathlib.Path(__file__).resolve().parents[1]
    / "scripts"
    / "provision_capture_media_azure.ps1"
)


class CaptureMediaInfrastructureContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.script = SCRIPT.read_text(encoding="utf-8")

    def test_supports_explicit_plan_apply_and_verify_modes(self):
        for mode in ("plan", "apply", "verify"):
            self.assertIn(f'"{mode}"', self.script)
        for parameter in (
            "ResourceGroupName",
            "StorageAccountName",
            "ContainerName",
            "WebAppName",
            "WebAppResourceGroupName",
            "MonthlyScanCapGb",
            "SoftDeleteDays",
        ):
            self.assertIn(parameter, self.script)
        self.assertIn("ConfirmApply", self.script)

    def test_enforces_private_oauth_only_storage_and_soft_delete(self):
        for setting in (
            "allow-blob-public-access",
            "allow-shared-key-access",
            "defaultToOAuthAuthentication",
            "min-tls-version",
            "TLS1_2",
            "https-only",
            "enable-delete-retention",
            "delete-retention-days",
        ):
            self.assertIn(setting, self.script)

    def test_defender_is_account_scoped_capped_and_fail_closed(self):
        for contract in (
            "defenderForStorageSettings/current",
            "overrideSubscriptionLevelSettings",
            "malwareScanning",
            "onUpload",
            "capGBPerMonth",
            "BlobIndexTags",
            "BlobSoftDelete",
            "75%",
            "100%",
        ):
            self.assertIn(contract, self.script)
        self.assertIn("sensitiveDataDiscovery", self.script)

    def test_managed_identity_roles_are_container_scoped_and_tag_read_only(self):
        self.assertIn("Storage Blob Data Contributor", self.script)
        self.assertIn(
            "Microsoft.Storage/storageAccounts/blobServices/containers/blobs/tags/read",
            self.script,
        )
        self.assertNotIn(
            "Microsoft.Storage/storageAccounts/blobServices/containers/blobs/tags/write",
            self.script,
        )
        self.assertNotIn("Storage Blob Data Owner", self.script)

    def test_json_payloads_use_temp_files_and_are_removed(self):
        self.assertGreaterEqual(
            self.script.count("[System.IO.Path]::GetTempFileName()"), 3
        )
        self.assertIn("Remove-Item -LiteralPath $ContainerPayloadPath", self.script)
        self.assertIn("Remove-Item -LiteralPath $StorageOAuthPayloadPath", self.script)
        self.assertIn("Remove-Item -LiteralPath $DefenderPayloadPath", self.script)
        self.assertIn("Remove-Item -LiteralPath $TagRolePayloadPath", self.script)

    def test_uses_only_nonsecret_app_settings_and_verify_reads_no_values(self):
        for setting in (
            "CAPTURE_PHOTO_ENABLED=false",
            "CAPTURE_MEDIA_BLOB_ACCOUNT_URL",
            "CAPTURE_MEDIA_BLOB_CONTAINER",
            "CAPTURE_PHOTO_MAX_BYTES",
            "CAPTURE_PHOTO_MAX_PIXELS",
            "CAPTURE_PHOTO_MAX_EDGE",
            "CAPTURE_PHOTO_DERIVATIVE_MAX_EDGE",
        ):
            self.assertIn(setting, self.script)
        lowered = self.script.lower()
        for forbidden in ("listkeys", "account key", "sas_token"):
            self.assertNotIn(forbidden, lowered)
        self.assertNotIn('"webapp", "config", "appsettings", "list"', self.script)
        self.assertIn(
            "verify does not read App Service setting values or credentials",
            self.script,
        )


if __name__ == "__main__":
    unittest.main()
