"""Regression checks for the PS-AUTH-JOURNEY-REPAIR-001 release template.

The runbook must remain safe to inspect locally: these tests validate the
tenant and Graph contract without acquiring a token or contacting Azure.
"""

from pathlib import Path
import re
import shutil
import subprocess
import unittest


ROOT = Path(__file__).resolve().parents[1]
RUNBOOK = ROOT / "docs" / "initiatives" / "PS-AUTH-JOURNEY-REPAIR-001" / "THREAT_AND_ROLLBACK.md"


class AuthReleaseTemplateTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source = RUNBOOK.read_text(encoding="utf-8")

    def test_external_id_graph_access_is_pinned_and_tenant_checked(self):
        self.assertIn("$entraTenantId = 'b6cac548-9b4b-43da-b366-e95be960ec2f'", self.source)
        self.assertIn(
            "$expectedExternalIdIssuer = 'https://peerslatemembers.ciamlogin.com/b6cac548-9b4b-43da-b366-e95be960ec2f/v2.0'",
            self.source,
        )
        self.assertIn("$appRegistrationAppId = 'a3f7a4d3-67c1-4c86-8653-dca3de75c99a'", self.source)
        self.assertIn("'webapp','auth','show'", self.source)
        self.assertIn("'{clientId:clientId,issuer:issuer}'", self.source)
        self.assertIn(
            "if ([string]$productionAuthPreflight.clientId -cne $appRegistrationAppId)",
            self.source,
        )
        self.assertIn(
            "if ([string]$productionAuthPreflight.issuer -cne $expectedExternalIdIssuer)",
            self.source,
        )
        self.assertIn(
            "'account','get-access-token','--tenant',$entraTenantId,'--resource-type','ms-graph'",
            self.source,
        )
        self.assertLess(
            self.source.index("$productionAuthPreflight ="),
            self.source.index("$graphAccessToken = Get-ExternalIdGraphAccessToken"),
        )
        self.assertIn(
            "if ([string]$payload.tenant -cne $entraTenantId)", self.source
        )
        self.assertIn("function Get-GraphApplication", self.source)
        self.assertIn("if ($matches.Count -ne 1)", self.source)
        self.assertIn("exactly one is required", self.source)
        self.assertNotIn("'ad','app'", self.source)
        self.assertNotIn("az rest", self.source)

    def test_token_is_memory_only_and_never_a_sanitized_artifact(self):
        self.assertIn("$graphAccessToken = Get-ExternalIdGraphAccessToken", self.source)
        self.assertIn('$graphHeaders = @{ Authorization = "Bearer $graphAccessToken" }', self.source)
        self.assertIn("Remove-Variable graphAccessToken", self.source)
        self.assertNotRegex(self.source, r"Save-SanitizedJson[^\n]*graphAccessToken")
        self.assertNotRegex(self.source, r"Set-Content[^\n]*graphAccessToken")
        self.assertNotRegex(self.source, r"Write-(?:Host|Output)[^\n]*graphAccessToken")

    def test_graph_patches_use_supported_web_fields_and_fresh_verification(self):
        supported_payload = re.search(
            r"function Get-SupportedWebPayload \{(?P<body>.*?)^\}",
            self.source,
            re.MULTILINE | re.DOTALL,
        )
        self.assertIsNotNone(supported_payload)
        body = supported_payload.group("body")
        for field in (
            "homePageUrl = $Web.homePageUrl",
            "logoutUrl = $Web.logoutUrl",
            "redirectUris = $redirectUris",
            "implicitGrantSettings = $Web.implicitGrantSettings",
        ):
            self.assertIn(field, body)
        self.assertNotIn("redirectUriSettings =", body)

        self.assertIn("function Invoke-GraphGetJson", self.source)
        self.assertIn("function Invoke-GraphPatchNoContent", self.source)
        self.assertIn("$response = Invoke-WebRequest @parameters", self.source)
        self.assertIn("if ($response.StatusCode -ne 204)", self.source)
        self.assertIn("UseBasicParsing = $true", self.source)
        self.assertIn("Invoke-GraphPatchNoContent 'Callback reduction PATCH'", self.source)
        self.assertIn("([pscustomobject]@{ web = $reductionWeb })", self.source)
        self.assertIn("$callbackWebBeforeReduction = [pscustomobject]@{ web = $reductionApplication.web }", self.source)
        self.assertIn("Assert-ExactWebSnapshot $callbackWebBefore.web $callbackWebBeforeReduction.web", self.source)
        self.assertIn("Assert-NonRedirectWebFieldsPreserved $callbackWebBefore.web $callbackWebAfter.web", self.source)
        self.assertIn("Invoke-GraphPatchNoContent 'Callback web restore PATCH'", self.source)
        self.assertIn("([pscustomobject]@{ web = $rollbackWeb })", self.source)
        self.assertIn("Assert-ExactWebSnapshot $callbackWebBefore.web $restoredCallbackWeb.web", self.source)
        self.assertLess(
            self.source.index("Assert-ExactWebSnapshot $callbackWebBefore.web $callbackWebBeforeReduction.web"),
            self.source.index("Invoke-GraphPatchNoContent 'Callback reduction PATCH'"),
        )
        self.assertLess(
            self.source.index("Invoke-GraphPatchNoContent 'Callback reduction PATCH'"),
            self.source.index("$callbackWebAfter = Get-CallbackWebSnapshot"),
        )

    def test_exact_pre_mutation_inventories_reject_unexpected_extras(self):
        self.assertIn("$expectedBoundHostNames = @('peerslate.com', $directAzureHostname, 'pete.peerslate.com')", self.source)
        self.assertIn("Production App Service bindings are not exactly the approved", self.source)
        self.assertIn("$expectedCallbacksBefore = @($approvedApexCallback", self.source)
        self.assertIn("Entra callbacks are not exactly the approved", self.source)
        self.assertIn("Compare-Object -CaseSensitive -ReferenceObject", self.source)

        expected_hosts = {
            "peerslate.com",
            "peerslate-pete-d9hhdeerd7frg2gc.centralus-01.azurewebsites.net",
            "pete.peerslate.com",
        }
        expected_callbacks = {
            "https://peerslate.com/.auth/login/aad/callback",
            "https://peerslate-pete-d9hhdeerd7frg2gc.centralus-01.azurewebsites.net/.auth/login/aad/callback",
            "https://pete.peerslate.com/.auth/login/aad/callback",
        }
        exact = lambda actual, expected: len(actual) == len(expected) and set(actual) == expected
        self.assertTrue(exact(list(expected_hosts), expected_hosts))
        self.assertTrue(exact(list(expected_callbacks), expected_callbacks))
        self.assertFalse(exact(list(expected_hosts) + ["unexpected.peerslate.com"], expected_hosts))
        self.assertFalse(
            exact(
                list(expected_callbacks)
                + ["https://unexpected.peerslate.com/.auth/login/aad/callback"],
                expected_callbacks,
            )
        )
        case_variant_callbacks = list(expected_callbacks)
        case_variant_callbacks[0] = case_variant_callbacks[0].replace("/.auth/", "/.AUTH/")
        self.assertFalse(exact(case_variant_callbacks, expected_callbacks))

    def test_patch_204_path_allows_immediate_fresh_verification(self):
        patch_function = self._extract_powershell_function("Invoke-GraphPatchNoContent")
        powershell = shutil.which("powershell") or shutil.which("pwsh")
        self.assertIsNotNone(powershell, "PowerShell is required to validate the release template")
        script = f"""
$ErrorActionPreference = 'Stop'
$graphHeaders = @{{ Authorization = 'Bearer test-token' }}
$script:patchComplete = $false
$script:freshVerificationRan = $false
function Invoke-WebRequest {{
    param($Method, $Uri, $Headers, $ContentType, $Body, $UseBasicParsing, $ErrorAction)
    if ($UseBasicParsing -ne $true) {{ throw 'Windows PowerShell basic parsing was not requested.' }}
    $script:patchComplete = $true
    return [pscustomobject]@{{ StatusCode = 204 }}
}}
{patch_function}
Invoke-GraphPatchNoContent 'mock callback reduction' 'https://graph.example/applications/mock' ([pscustomobject]@{{ web = [pscustomobject]@{{ redirectUris = @('https://peerslate.com/.auth/login/aad/callback') }} }})
function Get-CallbackWebSnapshot {{
    if (-not $script:patchComplete) {{ throw 'Fresh verification ran before PATCH completion.' }}
    $script:freshVerificationRan = $true
    return [pscustomobject]@{{ web = [pscustomobject]@{{ redirectUris = @('https://peerslate.com/.auth/login/aad/callback') }} }}
}}
$null = Get-CallbackWebSnapshot
if (-not $script:freshVerificationRan) {{ throw 'Fresh verification did not run after a 204 PATCH.' }}
"""
        result = subprocess.run(
            [powershell, "-NoProfile", "-NonInteractive", "-Command", script],
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(result.returncode, 0, result.stderr)

    def _extract_powershell_function(self, name):
        start = self.source.index(f"function {name} {{")
        depth = 0
        for index in range(start, len(self.source)):
            char = self.source[index]
            if char == "{":
                depth += 1
            elif char == "}":
                depth -= 1
                if depth == 0:
                    return self.source[start : index + 1]
        self.fail(f"Could not find the end of PowerShell function {name}")

    def test_www_callback_matcher_is_a_literal_hostname_match(self):
        pattern = r"^https://www\.peerslate\.com/"
        self.assertIn("$_ -match '" + pattern + "'", self.source)
        self.assertIsNotNone(re.search(pattern, "https://www.peerslate.com/.auth/login/aad/callback"))
        self.assertIsNone(re.search(pattern, "https://wwwXpeerslateYcom/.auth/login/aad/callback"))

    def test_callback_inventory_comparison_rejects_case_variants(self):
        powershell = shutil.which("powershell") or shutil.which("pwsh")
        self.assertIsNotNone(powershell, "PowerShell is required to validate the release template")
        script = """
$expected = @('https://peerslate.com/.auth/login/aad/callback')
$actual = @('https://peerslate.com/.AUTH/login/aad/callback')
$difference = Compare-Object -CaseSensitive -ReferenceObject ($expected | Sort-Object) -DifferenceObject ($actual | Sort-Object)
if (@($difference).Count -eq 0) { throw 'Case-variant callback unexpectedly matched.' }
"""
        result = subprocess.run(
            [powershell, "-NoProfile", "-NonInteractive", "-Command", script],
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(result.returncode, 0, result.stderr)


if __name__ == "__main__":
    unittest.main()
