<#
.SYNOPSIS
Plans, applies, or verifies the nonsecret Azure foundation for PS-VOICE-001.

.DESCRIPTION
This script uses Azure Resource Manager and Microsoft Entra RBAC only. It does
not retrieve credentials and does not create a public container or media URL.
ChatGPT Work owns any production apply. Codex may use explicit disposable
resource names for isolated proof.
#>
[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [ValidateSet("plan", "apply", "verify")]
    [string]$Mode,

    [Parameter(Mandatory = $true)]
    [string]$ResourceGroupName,

    [Parameter(Mandatory = $true)]
    [ValidatePattern('^[a-z0-9]{3,24}$')]
    [string]$StorageAccountName,

    [Parameter(Mandatory = $true)]
    [ValidatePattern('^[a-z0-9](?:[a-z0-9-]{1,61}[a-z0-9])?$')]
    [string]$ContainerName,

    [Parameter(Mandatory = $true)]
    [string]$WebAppName,

    [Parameter(Mandatory = $true)]
    [string]$AiServicesAccountName,

    [string]$Location = "eastus",
    [string]$SubscriptionId,
    [switch]$ConfirmApply
)

$ErrorActionPreference = "Stop"
$StorageRoleName = "Storage Blob Data Contributor"
$SpeechRoleName = "Cognitive Services Speech User"
$StorageRoleId = "ba92f5b4-2d11-453d-a403-e96b0029c9fe"
$SpeechRoleId = "f2dc8367-1007-4938-bd23-fe263f013447"
$SpeechApiVersion = "2025-10-15"
$VoiceLocale = "en-US"
$VoiceMaxBytes = "20971520"
$VoiceMaxDurationSeconds = "180"

function Invoke-AzureCli {
    param([Parameter(Mandatory = $true)][string[]]$Arguments)
    $output = & az @Arguments 2>&1
    if ($LASTEXITCODE -ne 0) {
        throw "Azure command failed without exposing provider output."
    }
    return ($output -join "`n").Trim()
}

function Assert-Equal {
    param(
        [Parameter(Mandatory = $true)]$Actual,
        [Parameter(Mandatory = $true)]$Expected,
        [Parameter(Mandatory = $true)][string]$Label
    )
    if ([string]$Actual -ne [string]$Expected) {
        throw "$Label verification failed."
    }
    Write-Output "PASS: $Label"
}

if ($SubscriptionId) {
    Invoke-AzureCli @("account", "set", "--subscription", $SubscriptionId) | Out-Null
}
$ResolvedSubscriptionId = Invoke-AzureCli @("account", "show", "--query", "id", "-o", "tsv")

$StorageResourceId = "/subscriptions/$ResolvedSubscriptionId/resourceGroups/$ResourceGroupName/providers/Microsoft.Storage/storageAccounts/$StorageAccountName"
$ContainerResourceId = "$StorageResourceId/blobServices/default/containers/$ContainerName"
$AiResourceId = "/subscriptions/$ResolvedSubscriptionId/resourceGroups/$ResourceGroupName/providers/Microsoft.CognitiveServices/accounts/$AiServicesAccountName"
$BlobAccountUrl = "https://$StorageAccountName.blob.core.windows.net"

if ($Mode -eq "plan") {
    Write-Output "PS-VOICE-001 Azure plan (no changes):"
    Write-Output "- Ensure resource group '$ResourceGroupName' in '$Location'."
    Write-Output "- Ensure private GPv2 storage '$StorageAccountName' with HTTPS, TLS1_2, public Blob access off, and shared-key access off."
    Write-Output "- Ensure private container '$ContainerName'."
    Write-Output "- Grant '$StorageRoleName' at the container scope to the '$WebAppName' managed identity."
    Write-Output "- Verify '$AiServicesAccountName' supports Speech with a custom Entra endpoint."
    Write-Output "- Grant '$SpeechRoleName' at the AI Services account scope to the same managed identity."
    Write-Output "- Set only VOICE_BLOB_ACCOUNT_URL, VOICE_BLOB_CONTAINER, VOICE_SPEECH_ENDPOINT, VOICE_SPEECH_API_VERSION, VOICE_LOCALE, VOICE_MAX_BYTES, and VOICE_MAX_DURATION_SECONDS."
    exit 0
}

if ($Mode -eq "apply") {
    if (-not $ConfirmApply) {
        throw "Apply requires -ConfirmApply and explicit reviewed resource names."
    }

    $ResourceGroupExists = Invoke-AzureCli @(
        "group", "exists", "--name", $ResourceGroupName, "-o", "tsv"
    )
    if ($ResourceGroupExists -ne "true") {
        Invoke-AzureCli @(
            "group", "create", "--name", $ResourceGroupName,
            "--location", $Location, "--output", "none"
        ) | Out-Null
    }

    $StorageExists = Invoke-AzureCli @(
        "storage", "account", "check-name", "--name", $StorageAccountName,
        "--query", "nameAvailable", "-o", "tsv"
    )
    if ($StorageExists -eq "true") {
        Invoke-AzureCli @(
            "storage", "account", "create",
            "--resource-group", $ResourceGroupName,
            "--name", $StorageAccountName,
            "--location", $Location,
            "--kind", "StorageV2",
            "--sku", "Standard_LRS",
            "--https-only", "true",
            "--min-tls-version", "TLS1_2",
            "--allow-blob-public-access", "false",
            "--allow-shared-key-access", "false",
            "--public-network-access", "Enabled",
            "--output", "none"
        ) | Out-Null
    }
    else {
        Invoke-AzureCli @(
            "storage", "account", "update",
            "--resource-group", $ResourceGroupName,
            "--name", $StorageAccountName,
            "--https-only", "true",
            "--min-tls-version", "TLS1_2",
            "--allow-blob-public-access", "false",
            "--allow-shared-key-access", "false",
            "--output", "none"
        ) | Out-Null
    }

    $ContainerApiUrl = "https://management.azure.com$ContainerResourceId`?api-version=2023-05-01"
    Invoke-AzureCli @(
        "rest", "--method", "put", "--url", $ContainerApiUrl,
        "--body", '{"properties":{"publicAccess":"None"}}',
        "--output", "none"
    ) | Out-Null

    $PrincipalId = Invoke-AzureCli @(
        "webapp", "identity", "show",
        "--resource-group", $ResourceGroupName,
        "--name", $WebAppName,
        "--query", "principalId", "-o", "tsv"
    )
    if (-not $PrincipalId) {
        throw "The web app system-assigned managed identity is missing."
    }

    $AiDetails = Invoke-AzureCli @(
        "cognitiveservices", "account", "show",
        "--resource-group", $ResourceGroupName,
        "--name", $AiServicesAccountName,
        "--query", "{kind:kind,endpoint:properties.endpoint,custom:properties.customSubDomainName}",
        "-o", "json"
    ) | ConvertFrom-Json
    if ($AiDetails.kind -notin @("AIServices", "CognitiveServices", "SpeechServices") -or
        -not $AiDetails.custom -or
        -not ([string]$AiDetails.endpoint).StartsWith("https://")) {
        throw "The existing AI Services account cannot prove Speech under managed identity. Stop for ChatGPT Work."
    }

    $StorageRoleCount = Invoke-AzureCli @(
        "role", "assignment", "list", "--assignee-object-id", $PrincipalId,
        "--scope", $ContainerResourceId, "--role", $StorageRoleName,
        "--query", "length(@)", "-o", "tsv"
    )
    if ([int]$StorageRoleCount -eq 0) {
        Invoke-AzureCli @(
            "role", "assignment", "create", "--assignee-object-id", $PrincipalId,
            "--assignee-principal-type", "ServicePrincipal", "--role", $StorageRoleId,
            "--scope", $ContainerResourceId, "--output", "none"
        ) | Out-Null
    }

    $SpeechRoleCount = Invoke-AzureCli @(
        "role", "assignment", "list", "--assignee-object-id", $PrincipalId,
        "--scope", $AiResourceId, "--role", $SpeechRoleName,
        "--query", "length(@)", "-o", "tsv"
    )
    if ([int]$SpeechRoleCount -eq 0) {
        Invoke-AzureCli @(
            "role", "assignment", "create", "--assignee-object-id", $PrincipalId,
            "--assignee-principal-type", "ServicePrincipal", "--role", $SpeechRoleId,
            "--scope", $AiResourceId, "--output", "none"
        ) | Out-Null
    }

    Invoke-AzureCli @(
        "webapp", "config", "appsettings", "set",
        "--resource-group", $ResourceGroupName,
        "--name", $WebAppName,
        "--settings",
        "VOICE_BLOB_ACCOUNT_URL=$BlobAccountUrl",
        "VOICE_BLOB_CONTAINER=$ContainerName",
        "VOICE_SPEECH_ENDPOINT=$($AiDetails.endpoint)",
        "VOICE_SPEECH_API_VERSION=$SpeechApiVersion",
        "VOICE_LOCALE=$VoiceLocale",
        "VOICE_MAX_BYTES=$VoiceMaxBytes",
        "VOICE_MAX_DURATION_SECONDS=$VoiceMaxDurationSeconds",
        "--output", "none"
    ) | Out-Null
    Write-Output "Apply completed. Run verify after RBAC propagation."
    exit 0
}

$StorageDetails = Invoke-AzureCli @(
    "storage", "account", "show",
    "--resource-group", $ResourceGroupName,
    "--name", $StorageAccountName,
    "--query", "{https:enableHttpsTrafficOnly,tls:minimumTlsVersion,public:allowBlobPublicAccess,shared:allowSharedKeyAccess,kind:kind}",
    "-o", "json"
) | ConvertFrom-Json
Assert-Equal $StorageDetails.kind "StorageV2" "GPv2 storage kind"
Assert-Equal $StorageDetails.https "True" "secure transfer"
Assert-Equal $StorageDetails.tls "TLS1_2" "minimum TLS"
Assert-Equal $StorageDetails.public "False" "public Blob access disabled"
Assert-Equal $StorageDetails.shared "False" "shared-key access disabled"

$ContainerPublicAccess = Invoke-AzureCli @(
    "rest", "--method", "get",
    "--url", "https://management.azure.com$ContainerResourceId`?api-version=2023-05-01",
    "--query", "properties.publicAccess", "-o", "tsv"
)
if ($ContainerPublicAccess -and $ContainerPublicAccess -ne "None") {
    throw "Container public access verification failed."
}
Write-Output "PASS: private container"

$PrincipalId = Invoke-AzureCli @(
    "webapp", "identity", "show", "--resource-group", $ResourceGroupName,
    "--name", $WebAppName, "--query", "principalId", "-o", "tsv"
)
$StorageRoleCount = Invoke-AzureCli @(
    "role", "assignment", "list", "--assignee-object-id", $PrincipalId,
    "--scope", $ContainerResourceId, "--role", $StorageRoleName,
    "--query", "length(@)", "-o", "tsv"
)
$SpeechRoleCount = Invoke-AzureCli @(
    "role", "assignment", "list", "--assignee-object-id", $PrincipalId,
    "--scope", $AiResourceId, "--role", $SpeechRoleName,
    "--query", "length(@)", "-o", "tsv"
)
if ([int]$StorageRoleCount -lt 1 -or [int]$SpeechRoleCount -lt 1) {
    throw "Managed-identity role verification failed."
}
Write-Output "PASS: managed-identity Blob and Speech roles"

$AiDetails = Invoke-AzureCli @(
    "cognitiveservices", "account", "show", "--resource-group", $ResourceGroupName,
    "--name", $AiServicesAccountName,
    "--query", "{kind:kind,endpoint:properties.endpoint,custom:properties.customSubDomainName}",
    "-o", "json"
) | ConvertFrom-Json
if ($AiDetails.kind -notin @("AIServices", "CognitiveServices", "SpeechServices") -or
    -not $AiDetails.custom -or -not ([string]$AiDetails.endpoint).StartsWith("https://")) {
    throw "Speech managed-identity capability verification failed. Stop for ChatGPT Work."
}
Write-Output "PASS: existing AI Services Speech endpoint"

Write-Output "PASS: verify does not read App Service setting values or credentials"
Write-Output "Known Voice settings require a signed-in Voice lifecycle check after apply: private upload, Azure transcription, owner playback/export, explicit deletion, and text Capture availability."
Write-Output "PS-VOICE-001 Azure control-plane verification passed; live functional verification remains required."
