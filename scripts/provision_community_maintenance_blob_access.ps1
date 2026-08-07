<#
.SYNOPSIS
Plans, applies, or verifies narrow Blob delete authority for Community maintenance.

.DESCRIPTION
Grants the dedicated Community maintenance workload identity Storage Blob Data
Contributor only on the approved private container. That identity must have no
management-plane role. This operation never reads a key, connection string,
SAS, App Service setting, Blob name, or member content.
#>
[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [ValidateSet("plan", "apply", "verify")]
    [string]$Mode,

    [Parameter(Mandatory = $true)]
    [ValidatePattern('^[0-9a-fA-F-]{36}$')]
    [string]$PrincipalObjectId,

    [Parameter(Mandatory = $true)]
    [ValidatePattern('^[a-z0-9]{3,24}$')]
    [string]$StorageAccountName,

    [Parameter(Mandatory = $true)]
    [ValidatePattern('^[a-z0-9](?:[a-z0-9-]{1,61}[a-z0-9])?$')]
    [string]$ContainerName,

    [string]$ResourceGroupName = "peerslate",
    [string]$SubscriptionId,
    [switch]$ConfirmApply
)

$ErrorActionPreference = "Stop"
$RoleName = "Storage Blob Data Contributor"
$RoleId = "ba92f5b4-2d11-453d-a403-e96b0029c9fe"
$AssignmentName = "0a1c352c-8847-4a3a-8d68-b1c10196ec76"

function Invoke-AzureCli {
    param([Parameter(Mandatory = $true)][string[]]$Arguments)
    $Prior = $ErrorActionPreference
    $ErrorActionPreference = "Continue"
    try {
        $Output = & az @Arguments 2>&1
        $ExitCode = $LASTEXITCODE
    }
    finally {
        $ErrorActionPreference = $Prior
    }
    if ($ExitCode -ne 0) {
        throw "Azure command failed without exposing provider output."
    }
    return ($Output -join "`n").Trim()
}

if ($SubscriptionId) {
    Invoke-AzureCli @("account", "set", "--subscription", $SubscriptionId) | Out-Null
}
$ResolvedSubscription = Invoke-AzureCli @(
    "account", "show", "--query", "id", "-o", "tsv"
)
$ContainerScope = "/subscriptions/$ResolvedSubscription/resourceGroups/$ResourceGroupName/providers/Microsoft.Storage/storageAccounts/$StorageAccountName/blobServices/default/containers/$ContainerName"
$ExpectedAssignmentId = "$ContainerScope/providers/Microsoft.Authorization/roleAssignments/$AssignmentName"

if ($Mode -eq "plan") {
    Write-Output "PLAN: grant '$RoleName' to the scheduled-maintenance principal at only the approved container scope."
    exit 0
}

if ($Mode -eq "apply" -and -not $ConfirmApply) {
    throw "Apply requires -ConfirmApply."
}

# A fresh service principal must not inherit authority through an Entra group.
# This protected provisioning command runs with operator Graph read authority;
# the scheduled workload identity does not receive that authority.
$GroupsJson = Invoke-AzureCli @(
    "rest", "--method", "GET",
    "--url", "https://graph.microsoft.com/v1.0/servicePrincipals/$PrincipalObjectId/transitiveMemberOf/microsoft.graph.group?`$select=id",
    "--query", "value[].id", "-o", "json"
)
$Groups = @($GroupsJson | ConvertFrom-Json)
if ($Groups.Count -ne 0) {
    throw "Community maintenance identity has inherited group membership."
}

function Get-AuthorityAssignments {
    $Json = Invoke-AzureCli @(
        "role", "assignment", "list",
        "--assignee-object-id", $PrincipalObjectId,
        "--all", "--include-inherited", "--query",
        "[].{id:id,role:roleDefinitionName,scope:scope}",
        "-o", "json"
    )
    return @($Json | ConvertFrom-Json)
}

function Test-AuthorityAssignments {
    param(
        [Parameter(Mandatory = $true)]
        [AllowEmptyCollection()]
        [object[]]$Assignments,
        [Parameter(Mandatory = $true)][bool]$AllowMissing
    )
    $Approved = @(
        $Assignments | Where-Object {
            $_.role -eq $RoleName -and
            $_.scope -eq $ContainerScope -and
            $_.id -eq $ExpectedAssignmentId
        }
    )
    $Unexpected = @(
        $Assignments | Where-Object {
            $_.role -ne $RoleName -or
            $_.scope -ne $ContainerScope -or
            $_.id -ne $ExpectedAssignmentId
        }
    )
    $CountIsSafe = $Approved.Count -eq 1
    if ($AllowMissing) {
        $CountIsSafe = $Approved.Count -le 1
    }
    if (-not $CountIsSafe -or $Unexpected.Count -ne 0) {
        throw "Community maintenance Blob authority verification failed."
    }
    return $Approved.Count
}

$Assignments = @(Get-AuthorityAssignments)
$ApprovedCount = Test-AuthorityAssignments `
    -Assignments $Assignments `
    -AllowMissing ($Mode -eq "apply")

if ($Mode -eq "apply" -and $ApprovedCount -eq 0) {
    try {
        Invoke-AzureCli @(
            "role", "assignment", "create",
            "--assignee-object-id", $PrincipalObjectId,
            "--assignee-principal-type", "ServicePrincipal",
            "--role", $RoleId,
            "--scope", $ContainerScope,
            "--name", $AssignmentName,
            "--only-show-errors", "-o", "none"
        ) | Out-Null
        $Assignments = @(Get-AuthorityAssignments)
        Test-AuthorityAssignments `
            -Assignments $Assignments `
            -AllowMissing $false | Out-Null
    }
    catch {
        # The preflight proved no approved role existed. Remove only the exact
        # role this invocation may have created, even if create returned an
        # ambiguous provider failure after durable success.
        try {
            Invoke-AzureCli @(
                "role", "assignment", "delete",
                "--ids", $ExpectedAssignmentId,
                "--only-show-errors"
            ) | Out-Null
        }
        catch {
            throw "Community maintenance Blob authority failed and compensating removal could not be verified."
        }
        throw "Community maintenance Blob authority failed; the newly created role was removed."
    }
}
Write-Output "PASS: one container-scoped '$RoleName' assignment; no other Azure role."
