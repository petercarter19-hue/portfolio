import pathlib
import unittest


SCRIPT = (
    pathlib.Path(__file__).resolve().parents[1]
    / "scripts"
    / "provision_voice_capture_azure.ps1"
)


class VoiceInfrastructureContractTests(unittest.TestCase):
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
            "AiServicesAccountName",
        ):
            self.assertIn(parameter, self.script)

    def test_enforces_private_storage_and_managed_identity_roles(self):
        for setting in (
            "allow-blob-public-access",
            "allow-shared-key-access",
            "min-tls-version",
            "TLS1_2",
            "https-only",
            "Storage Blob Data Contributor",
            "Cognitive Services Speech User",
        ):
            self.assertIn(setting, self.script)

    def test_uses_only_nonsecret_app_settings(self):
        for setting in (
            "VOICE_BLOB_ACCOUNT_URL",
            "VOICE_BLOB_CONTAINER",
            "VOICE_SPEECH_ENDPOINT",
            "VOICE_SPEECH_API_VERSION",
            "VOICE_LOCALE",
            "VOICE_MAX_BYTES",
            "VOICE_MAX_DURATION_SECONDS",
        ):
            self.assertIn(setting, self.script)
        lowered = self.script.lower()
        for forbidden in ("listkeys", "account key", "speech_key", "sas_token"):
            self.assertNotIn(forbidden, lowered)

    def test_verify_never_reads_app_setting_values_or_credentials(self):
        self.assertNotIn(
            '"webapp", "config", "appsettings", "list"',
            self.script,
        )
        self.assertNotIn("$Settings =", self.script)
        self.assertIn(
            "does not read App Service setting values",
            self.script,
        )
        self.assertIn("signed-in Voice lifecycle", self.script)


if __name__ == "__main__":
    unittest.main()
