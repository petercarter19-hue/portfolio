<#
.SYNOPSIS
Plans, applies, or verifies the nonsecret Azure foundation for private Capture Media.

.DESCRIPTION
This script uses Azure Resource Manager and Microsoft Entra RBAC only. It never
retrieves credentials, shared-key material, SAS tokens, App Service setting values, or
member content. Production apply remains gated on isolated proof and designated
manager acceptance. Plan mode is nonmutating.
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

    [string]$WebAppResourceGroupName,
    [string]$Location = "centralus",
    [string]$SubscriptionId,
    [ValidateRange(1, 10000)]
    [int]$MonthlyScanCapGb = 10,
    [ValidateRange(1, 365)]
    [int]$SoftDeleteDays = 7,
    [switch]$SkipAppSettings,
    [switch]$ConfirmApply
)

$ErrorActionPreference = "Stop"
$StorageRoleName = "Storage Blob Data Contributor"
$StorageRoleId = "ba92f5b4-2d11-453d-a403-e96b0029c9fe"
$TagReaderRoleName = "$StorageAccountName-CaptureMediaTagReader"
$DefenderApiVersion = "2025-09-01-preview"
$StorageApiVersion = "2023-05-01"
$PhotoMaxBytes = "10485760"
$PhotoMaxPixels = "20000000"
$PhotoMaxEdge = "8192"
$PhotoDerivativeMaxEdge = "2400"

function Invoke-AzureCli {
    param([Parameter(Mandatory = $true)][string[]]$Arguments)
    $PriorErrorActionPreference = $ErrorActionPreference
    $ErrorActionPreference = "Continue"
    try {
        $output = & az @Arguments 2>&1
        $AzureExitCode = $LASTEXITCODE
    }
    finally {
        $ErrorActionPreference = $PriorErrorActionPreference
    }
    if ($AzureExitCode -ne 0) {
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

function Get-AzureRoleAssignmentCount {
    param(
        [Parameter(Mandatory = $true)][string]$PrincipalId,
        [Parameter(Mandatory = $true)][string]$Scope,
        [Parameter(Mandatory = $true)][string]$RoleName
    )
    $assignmentIds = Invoke-AzureCli @(
        "role", "assignment", "list", "--assignee-object-id", $PrincipalId,
        "--scope", $Scope, "--role", $RoleName,
        "--query", "[].id", "-o", "tsv"
    )
    if (-not $assignmentIds) {
        return 0
    }
    return @(
        ($assignmentIds -split "`r?`n") | Where-Object { $_ }
    ).Count
}

if ($SubscriptionId) {
    Invoke-AzureCli @("account", "set", "--subscription", $SubscriptionId) | Out-Null
}
$ResolvedSubscriptionId = Invoke-AzureCli @(
    "account", "show", "--query", "id", "-o", "tsv"
)
$ResolvedWebAppResourceGroupName = if ($WebAppResourceGroupName) {
    $WebAppResourceGroupName
}
else {
    $ResourceGroupName
}
$StorageResourceId = "/subscriptions/$ResolvedSubscriptionId/resourceGroups/$ResourceGroupName/providers/Microsoft.Storage/storageAccounts/$StorageAccountName"
$ContainerResourceId = "$StorageResourceId/blobServices/default/containers/$ContainerName"
$DefenderResourceId = "$StorageResourceId/providers/Microsoft.Security/defenderForStorageSettings/current"
$BlobAccountUrl = "https://$StorageAccountName.blob.core.windows.net"

if ($Mode -eq "plan") {
    Write-Output "PS-CAPTURE-MEDIA-001 Azure plan (no changes):"
    Write-Output "- Ensure separate GPv2 Standard_LRS storage '$StorageAccountName' in '$ResourceGroupName' / '$Location'."
    Write-Output "- Enforce HTTPS, TLS1_2, public Blob access off, shared-key access off, and default OAuth authentication."
    Write-Output "- Ensure private container '$ContainerName' and Blob soft delete for $SoftDeleteDays days."
    Write-Output "- Enable account-level Defender for Storage on-upload malware scanning with a $MonthlyScanCapGb GB/month cap."
    Write-Output "- Keep sensitive-data discovery off; enable BlobIndexTags scan results and BlobSoftDelete automated response."
    Write-Output "- Grant '$StorageRoleName' and a tag-read-only custom role at the container scope to '$WebAppName'."
    if ($SkipAppSettings) {
        Write-Output "- Isolated proof: do not alter App Service settings."
    }
    else {
        Write-Output "- Set only nonsecret Capture Media account/container/limit settings and CAPTURE_PHOTO_ENABLED=false."
    }
    Write-Output "- Defender emits built-in security alerts at 75% and 100% of the monthly scan cap; scan errors, malicious findings, and deletion backlog still require operational evidence before launch."
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

    $StorageNameAvailable = Invoke-AzureCli @(
        "storage", "account", "check-name", "--name", $StorageAccountName,
        "--query", "nameAvailable", "-o", "tsv"
    )
    if ($StorageNameAvailable -eq "true") {
        Invoke-AzureCli @(
            "storage", "account", "create",
            "--resource-group", $ResourceGroupName,
            "--name", $StorageAccountName,
            "--location", $Location,
            "--kind", "StorageV2", "--sku", "Standard_LRS",
            "--https-only", "true", "--min-tls-version", "TLS1_2",
            "--allow-blob-public-access", "false",
            "--allow-shared-key-access", "false",
            "--default-action", "Allow",
            "--public-network-access", "Enabled",
            "--output", "none"
        ) | Out-Null
    }

    Invoke-AzureCli @(
        "storage", "account", "update",
        "--resource-group", $ResourceGroupName,
        "--name", $StorageAccountName,
        "--https-only", "true", "--min-tls-version", "TLS1_2",
        "--allow-blob-public-access", "false",
        "--allow-shared-key-access", "false",
        "--output", "none"
    ) | Out-Null

    $StorageOAuthPayloadPath = [System.IO.Path]::GetTempFileName()
    try {
        [System.IO.File]::WriteAllText(
            $StorageOAuthPayloadPath,
            '{"properties":{"defaultToOAuthAuthentication":true}}',
            [System.Text.UTF8Encoding]::new($false)
        )
        Invoke-AzureCli @(
            "rest", "--method", "patch",
            "--url", "https://management.azure.com$StorageResourceId`?api-version=$StorageApiVersion",
            "--body", "@$StorageOAuthPayloadPath", "--output", "none"
        ) | Out-Null
    }
    finally {
        Remove-Item -LiteralPath $StorageOAuthPayloadPath -Force -ErrorAction SilentlyContinue
    }

    Invoke-AzureCli @(
        "storage", "account", "blob-service-properties", "update",
        "--resource-group", $ResourceGroupName,
        "--account-name", $StorageAccountName,
        "--enable-delete-retention", "true",
        "--delete-retention-days", [string]$SoftDeleteDays,
        "--output", "none"
    ) | Out-Null

    $ContainerPayloadPath = [System.IO.Path]::GetTempFileName()
    try {
        [System.IO.File]::WriteAllText(
            $ContainerPayloadPath,
            '{"properties":{"publicAccess":"None"}}',
            [System.Text.UTF8Encoding]::new($false)
        )
        Invoke-AzureCli @(
            "rest", "--method", "put",
            "--url", "https://management.azure.com$ContainerResourceId`?api-version=$StorageApiVersion",
            "--body", "@$ContainerPayloadPath", "--output", "none"
        ) | Out-Null
    }
    finally {
        Remove-Item -LiteralPath $ContainerPayloadPath -Force -ErrorAction SilentlyContinue
    }

    $DefenderPayloadPath = [System.IO.Path]::GetTempFileName()
    try {
        $DefenderPayload = @{
            properties = @{
                isEnabled = $true
                overrideSubscriptionLevelSettings = $true
                sensitiveDataDiscovery = @{ isEnabled = $false }
                malwareScanning = @{
                    onUpload = @{
                        isEnabled = $true
                        capGBPerMonth = $MonthlyScanCapGb
                    }
                    blobScanResultsOptions = "BlobIndexTags"
                    automatedResponse = "BlobSoftDelete"
                }
            }
        } | ConvertTo-Json -Depth 8 -Compress
        [System.IO.File]::WriteAllText(
            $DefenderPayloadPath, $DefenderPayload,
            [System.Text.UTF8Encoding]::new($false)
        )
        Invoke-AzureCli @(
            "rest", "--method", "put",
            "--url", "https://management.azure.com$DefenderResourceId`?api-version=$DefenderApiVersion",
            "--body", "@$DefenderPayloadPath", "--output", "none"
        ) | Out-Null
    }
    finally {
        Remove-Item -LiteralPath $DefenderPayloadPath -Force -ErrorAction SilentlyContinue
    }

    $PrincipalId = Invoke-AzureCli @(
        "webapp", "identity", "show", "--resource-group", $ResolvedWebAppResourceGroupName,
        "--name", $WebAppName, "--query", "principalId", "-o", "tsv"
    )
    if (-not $PrincipalId) {
        throw "The web app system-assigned managed identity is missing."
    }

    $StorageRoleCount = Get-AzureRoleAssignmentCount `
        -PrincipalId $PrincipalId -Scope $ContainerResourceId -RoleName $StorageRoleName
    if ([int]$StorageRoleCount -eq 0) {
        Invoke-AzureCli @(
            "role", "assignment", "create", "--assignee-object-id", $PrincipalId,
            "--assignee-principal-type", "ServicePrincipal", "--role", $StorageRoleId,
            "--scope", $ContainerResourceId, "--output", "none"
        ) | Out-Null
    }

    $TagRolePayloadPath = [System.IO.Path]::GetTempFileName()
    try {
        $TagRolePayload = @{
            Name = $TagReaderRoleName
            IsCustom = $true
            Description = "Read Defender-owned Blob index tags for private Capture Media."
            Actions = @()
            NotActions = @()
            DataActions = @(
                "Microsoft.Storage/storageAccounts/blobServices/containers/blobs/tags/read"
            )
            NotDataActions = @()
            AssignableScopes = @($StorageResourceId)
        } | ConvertTo-Json -Depth 6
        [System.IO.File]::WriteAllText(
            $TagRolePayloadPath, $TagRolePayload,
            [System.Text.UTF8Encoding]::new($false)
        )
        $ExistingTagRoleJson = Invoke-AzureCli @(
            "role", "definition", "list", "--name", $TagReaderRoleName, "-o", "json"
        )
        $ExistingTagRole = @($ExistingTagRoleJson | ConvertFrom-Json)[0]
        if ($ExistingTagRole) {
            $ExistingPermission = @($ExistingTagRole.permissions)[0]
            if (@($ExistingPermission.dataActions).Count -ne 1 -or
                $ExistingPermission.dataActions[0] -ne "Microsoft.Storage/storageAccounts/blobServices/containers/blobs/tags/read" -or
                @($ExistingPermission.actions).Count -ne 0 -or
                @($ExistingPermission.notDataActions).Count -ne 0 -or
                $StorageResourceId -notin @($ExistingTagRole.assignableScopes)) {
                throw "The existing Capture Media tag-reader role differs from the reviewed least-privilege contract."
            }
        }
        else {
            Invoke-AzureCli @(
                "role", "definition", "create", "--role-definition", "@$TagRolePayloadPath",
                "--output", "none"
            ) | Out-Null
        }
    }
    finally {
        Remove-Item -LiteralPath $TagRolePayloadPath -Force -ErrorAction SilentlyContinue
    }

    $TagRoleCount = Get-AzureRoleAssignmentCount `
        -PrincipalId $PrincipalId -Scope $ContainerResourceId -RoleName $TagReaderRoleName
    if ([int]$TagRoleCount -eq 0) {
        Invoke-AzureCli @(
            "role", "assignment", "create", "--assignee-object-id", $PrincipalId,
            "--assignee-principal-type", "ServicePrincipal", "--role", $TagReaderRoleName,
            "--scope", $ContainerResourceId, "--output", "none"
        ) | Out-Null
    }

    if (-not $SkipAppSettings) {
        Invoke-AzureCli @(
            "webapp", "config", "appsettings", "set",
            "--resource-group", $ResolvedWebAppResourceGroupName, "--name", $WebAppName,
            "--settings",
            "CAPTURE_PHOTO_ENABLED=false",
            "CAPTURE_MEDIA_BLOB_ACCOUNT_URL=$BlobAccountUrl",
            "CAPTURE_MEDIA_BLOB_CONTAINER=$ContainerName",
            "CAPTURE_PHOTO_MAX_BYTES=$PhotoMaxBytes",
            "CAPTURE_PHOTO_MAX_PIXELS=$PhotoMaxPixels",
            "CAPTURE_PHOTO_MAX_EDGE=$PhotoMaxEdge",
            "CAPTURE_PHOTO_DERIVATIVE_MAX_EDGE=$PhotoDerivativeMaxEdge",
            "--output", "none"
        ) | Out-Null
    }
    Write-Output "Apply completed with Photo still disabled. Run verify after RBAC propagation."
    exit 0
}

$StorageDetails = Invoke-AzureCli @(
    "storage", "account", "show", "--resource-group", $ResourceGroupName,
    "--name", $StorageAccountName,
    "--query", "{https:enableHttpsTrafficOnly,tls:minimumTlsVersion,public:allowBlobPublicAccess,shared:allowSharedKeyAccess,oauth:defaultToOAuthAuthentication,kind:kind,sku:sku.name}",
    "-o", "json"
) | ConvertFrom-Json
Assert-Equal $StorageDetails.kind "StorageV2" "GPv2 storage kind"
Assert-Equal $StorageDetails.sku "Standard_LRS" "storage redundancy"
Assert-Equal $StorageDetails.https "True" "secure transfer"
Assert-Equal $StorageDetails.tls "TLS1_2" "minimum TLS"
Assert-Equal $StorageDetails.public "False" "public Blob access disabled"
Assert-Equal $StorageDetails.shared "False" "shared-key access disabled"
Assert-Equal $StorageDetails.oauth "True" "default OAuth authentication"

$ContainerPublicAccess = Invoke-AzureCli @(
    "rest", "--method", "get",
    "--url", "https://management.azure.com$ContainerResourceId`?api-version=$StorageApiVersion",
    "--query", "properties.publicAccess", "-o", "tsv"
)
if ($ContainerPublicAccess -and $ContainerPublicAccess -ne "None") {
    throw "Container public access verification failed."
}
Write-Output "PASS: private Capture Media container"

$DeleteRetention = Invoke-AzureCli @(
    "storage", "account", "blob-service-properties", "show",
    "--resource-group", $ResourceGroupName, "--account-name", $StorageAccountName,
    "--query", "{enabled:deleteRetentionPolicy.enabled,days:deleteRetentionPolicy.days}",
    "-o", "json"
) | ConvertFrom-Json
Assert-Equal $DeleteRetention.enabled "True" "Blob soft delete enabled"
Assert-Equal $DeleteRetention.days ([string]$SoftDeleteDays) "Blob soft delete retention"

$DefenderDetails = Invoke-AzureCli @(
    "rest", "--method", "get",
    "--url", "https://management.azure.com$DefenderResourceId`?api-version=$DefenderApiVersion",
    "--query", "properties", "-o", "json"
) | ConvertFrom-Json
Assert-Equal $DefenderDetails.isEnabled "True" "Defender for Storage enabled"
Assert-Equal $DefenderDetails.overrideSubscriptionLevelSettings "True" "account Defender override"
Assert-Equal $DefenderDetails.malwareScanning.onUpload.isEnabled "True" "on-upload malware scanning"
Assert-Equal $DefenderDetails.malwareScanning.onUpload.capGBPerMonth ([string]$MonthlyScanCapGb) "monthly scan cap"
Assert-Equal $DefenderDetails.malwareScanning.blobScanResultsOptions "BlobIndexTags" "Defender scan-result tags"
Assert-Equal $DefenderDetails.malwareScanning.automatedResponse "BlobSoftDelete" "malicious-Blob automated response"
Assert-Equal $DefenderDetails.sensitiveDataDiscovery.isEnabled "False" "sensitive-data discovery remains out of scope"

$PrincipalId = Invoke-AzureCli @(
    "webapp", "identity", "show", "--resource-group", $ResolvedWebAppResourceGroupName,
    "--name", $WebAppName, "--query", "principalId", "-o", "tsv"
)
$StorageRoleCount = Get-AzureRoleAssignmentCount `
    -PrincipalId $PrincipalId -Scope $ContainerResourceId -RoleName $StorageRoleName
$TagRoleCount = Get-AzureRoleAssignmentCount `
    -PrincipalId $PrincipalId -Scope $ContainerResourceId -RoleName $TagReaderRoleName
if ([int]$StorageRoleCount -lt 1 -or [int]$TagRoleCount -lt 1) {
    throw "Managed-identity container role verification failed."
}
Write-Output "PASS: container-scoped Blob contributor and tag-reader roles"

$TagRole = Invoke-AzureCli @(
    "role", "definition", "list", "--name", $TagReaderRoleName,
    "--query", "[0].permissions[0]", "-o", "json"
) | ConvertFrom-Json
$ExpectedTagRead = "Microsoft.Storage/storageAccounts/blobServices/containers/blobs/tags/read"
if (@($TagRole.dataActions).Count -ne 1 -or $TagRole.dataActions[0] -ne $ExpectedTagRead -or
    @($TagRole.actions).Count -ne 0 -or @($TagRole.notDataActions).Count -ne 0) {
    throw "The custom role is not limited to Blob tag read."
}
if (($TagRole | ConvertTo-Json -Depth 6).ToLowerInvariant().Contains("tags/write")) {
    throw "The application role unexpectedly includes Blob tag write."
}
Write-Output "PASS: Defender Blob tag role is read-only"

Write-Output "PASS: Defender cap is configured for built-in 75% and 100% security-alert thresholds"
Write-Output "PASS: verify does not read App Service setting values or credentials"
Write-Output "Known Photo settings require a signed-in synthetic lifecycle after release: private upload, fail-closed scan, safe derivative, owner preview/export, explicit confirmation/deletion, and Type/Voice availability."
Write-Output "PS-CAPTURE-MEDIA-001 Azure control-plane verification passed; live functional verification remains gated."
