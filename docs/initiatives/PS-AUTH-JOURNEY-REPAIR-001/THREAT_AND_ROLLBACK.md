# PS-AUTH-JOURNEY-REPAIR-001 - Threat and rollback contract

## Threat controls

| Threat | Control in this package | Negative evidence |
| --- | --- | --- |
| A malformed Easy Auth header is treated as an anonymous browser | Dedicated sibling AuthenticationPrincipalInvalid; global generic recovery instead of a provider redirect | malformed header on HTML and JSON protected routes returns a private/no-store recovery response |
| A valid platform principal is mistaken for an application member without a usable account result | IdentityMappingError remains separate from absent authentication | no-row mapping renders generic account recovery and cannot fall through to a public/anonymous view |
| A valid but unmapped principal reveals an owner-only route or its data endpoint | Control Room authorization catches IdentityMappingError with the same fail-closed path as storage failure | mapped non-owner and unmapped-principal denials have identical 404 status, content type, and body for both routes |
| Header/nav/session checks wake Azure SQL or upsert accounts | get_current_principal() and /auth/session validate/cache claims only | principal/session tests assert no database_service.first_row call |
| A return destination escapes the private application | bounded /app parser rejects schemes, netloc, fragments, controls, backslashes, double slashes, auth paths, and oversized values | redirect-attack table verifies the fixed completion target |
| Callback retry loops hide a broken session | /auth/complete renders manual recovery for a missing principal; invalid sessions do not launch the provider | completion/malformed-session tests assert no provider-login Location |
| A shared/public cache or bfcache exposes stale account controls | principal-aware private, no-store; bounded public reconciliation and one private bfcache server reauthorization reload | focused HTML/JS tests cover state preservation on 503, non-JSON, unknown payload, and bfcache behavior |
| Host-header or forwarded-host confusion sends requests to attacker-controlled URLs | opt-in fixed-target canonical redirects use validated request.host, fixed config, and no x_host | canonical tests cover www, Azure host, unknown host, unsafe method, and forged X-Forwarded-Host |

## Data and privacy boundary

This package makes no schema, migration, stored-procedure, provider-tenant,
secret, password, token, credential, account-linking, or production-setting
mutation. It does not log or render raw claims, header bytes, mapping error
detail, or account data from an error path.

## Stop conditions

Stop release consideration if any test permits an invalid or mapping-failed
session to become anonymous, follows a provider redirect automatically,
performs database work from /auth/session, forwards a non-GET/HEAD request to
a canonical host, trusts X-Forwarded-Host, exposes detail in a recovery
response, distinguishes an unmapped principal from a neutral Control Room
denial, or conflicts with the preserved Owner Home runtime surface.

## Current live alias scope

The current live alternate sign-in aliases are exactly the App Service default
hostname and `pete.peerslate.com`; the former is discovered from the production
App Service inventory by the template below. `peerslate.com` remains the fixed
canonical destination. As verified on 2026-08-02, `www.peerslate.com` has no
DNS record, App Service binding, or Entra callback. It is deliberately outside
this cutover: do not create or bind it, add a callback, or add it to the alias
test loop. Code and focused tests retain their existing hypothetical-`www`
protection. If a future owner-authorized slice introduces `www`, it must first
establish DNS and an App Service binding/TLS, then verify canonical GET, HEAD,
and unsafe-method behavior before `www` is used or added to Entra.

The pre-mutation inventories must have no arbitrary extras: App Service
`hostNames` must be exactly the apex, the discovered direct Azure hostname, and
`pete.peerslate.com`; Entra callbacks must be exactly the corresponding three
case-exact `/.auth/login/aad/callback` URIs. A duplicate, case variant, `www`,
or any other additional binding/callback stops the cutover before a setting or
Graph PATCH occurs.

## Azure staged release and fail-fast evidence templates

Current pre-cutover evidence records 17 exchanges in 18 seconds ending in
AADSTS50196, three host-scoped app-registration callbacks, an 8-hour Easy Auth
cookie with 72-hour grace, and no Conditional Access policy. This package does
not change session duration or offline_access in the initial cutover. The
optional malformed Microsoft-account provider and same-email admin/customer
findings are deferred: addressing them needs provider or administrator changes
outside this package.

The forward release order is fixed: deploy merged code with canonical
enforcement off, capture sanitized evidence, enable the two canonical settings,
verify aliases and unsafe methods, reduce callbacks to the approved apex only,
then obtain owner credential acceptance. Do not output, commit, or attach full
app-settings results, secrets, cookie values, tokens, credentials, or a raw
credential test transcript.

The templates below are operator instructions, not commands run by this
package. They write only sanitized, temporary local evidence. Every native az
and curl.exe call goes through a helper that checks LASTEXITCODE immediately.
Every native CLI JSON response is captured first, checked for native success,
parsed and validated before it is written as evidence. Graph responses are
freshly queried through a fail-fast REST helper. The app registration is in the PeerSlate
Members Entra External ID tenant, not the production subscription tenant. Its
Microsoft Graph access token is held only in process memory and is neither
written, emitted, nor attached to evidence. Before Graph token acquisition,
the template queries the production Easy Auth configuration and requires the
exact registered client ID and External ID issuer.

~~~powershell
$ErrorActionPreference = 'Stop'

$subscriptionId = '<AZURE_SUBSCRIPTION_ID>'
$resourceGroup = '<WEBAPP_RESOURCE_GROUP>'
$webAppName = '<WEBAPP_NAME>'
# Pinned from the verified production PEERSLATE_AUTH_ISSUER / External ID
# registration. The Azure subscription tenant is not an authority for this app.
$entraTenantId = 'b6cac548-9b4b-43da-b366-e95be960ec2f'
$expectedExternalIdIssuer = 'https://peerslatemembers.ciamlogin.com/b6cac548-9b4b-43da-b366-e95be960ec2f/v2.0'
$appRegistrationAppId = 'a3f7a4d3-67c1-4c86-8653-dca3de75c99a'
$approvedApexCallback = 'https://peerslate.com/.auth/login/aad/callback'
$evidenceDirectory = Join-Path $env:TEMP ('peerslate-auth-journey-' + (Get-Date -Format 'yyyyMMdd-HHmmss'))
New-Item -ItemType Directory -Path $evidenceDirectory -Force | Out-Null

function Convert-NativeJson {
    param([string]$Label, [object]$RawOutput)
    $jsonText = ($RawOutput | Out-String).Trim()
    if ([string]::IsNullOrWhiteSpace($jsonText)) { throw "$Label returned no JSON." }
    try { return $jsonText | ConvertFrom-Json } catch { throw "$Label did not return valid JSON: $($_.Exception.Message)" }
}

function Invoke-AzJson {
    param([string]$Label, [string[]]$Arguments)
    $raw = & az @Arguments
    if ($LASTEXITCODE -ne 0) { throw "$Label failed with exit code $LASTEXITCODE." }
    return Convert-NativeJson $Label $raw
}

function Invoke-AzQuiet {
    param([string]$Label, [string[]]$Arguments)
    & az @Arguments
    if ($LASTEXITCODE -ne 0) { throw "$Label failed with exit code $LASTEXITCODE." }
}

function Invoke-CurlHeaders {
    param([string]$Label, [string[]]$Arguments, [string]$HeaderPath)
    & curl.exe @Arguments --output NUL --dump-header $HeaderPath
    if ($LASTEXITCODE -ne 0) { throw "$Label failed with exit code $LASTEXITCODE." }
}

function Save-SanitizedJson {
    param([object]$Value, [string]$LeafName)
    $path = Join-Path $evidenceDirectory $LeafName
    $Value | ConvertTo-Json -Depth 12 | Set-Content -LiteralPath $path -Encoding utf8
    return $path
}

function Get-ExternalIdGraphAccessToken {
    # Capture the token only in a local variable; never serialize or emit it.
    $payload = Invoke-AzJson 'External ID Microsoft Graph access token' @('account','get-access-token','--tenant',$entraTenantId,'--resource-type','ms-graph','--query','{accessToken:accessToken,tenant:tenant}','--output','json')
    if ([string]$payload.tenant -cne $entraTenantId) { throw 'Microsoft Graph token tenant does not match the pinned External ID tenant.' }
    $token = [string]$payload.accessToken
    if ([string]::IsNullOrWhiteSpace($token)) { throw 'Microsoft Graph access-token query returned no token.' }
    return $token
}

function Invoke-GraphGetJson {
    param([string]$Label, [string]$Uri)
    try {
        $parameters = @{ Method = 'GET'; Uri = $Uri; Headers = $graphHeaders; ErrorAction = 'Stop' }
        $response = Invoke-RestMethod @parameters
    } catch {
        throw "$Label failed: $($_.Exception.Message)"
    }
    if ($null -eq $response) { throw "$Label returned no JSON." }
    return $response
}

function Invoke-GraphPatchNoContent {
    param([string]$Label, [string]$Uri, [object]$Body)
    try {
        $parameters = @{
            Method = 'PATCH'
            Uri = $Uri
            Headers = $graphHeaders
            ContentType = 'application/json'
            Body = ($Body | ConvertTo-Json -Depth 20 -Compress)
            UseBasicParsing = $true
            ErrorAction = 'Stop'
        }
        $response = Invoke-WebRequest @parameters
    } catch {
        throw "$Label failed: $($_.Exception.Message)"
    }
    if ($response.StatusCode -ne 204) { throw "$Label returned HTTP $($response.StatusCode), expected 204 No Content." }
}

function Get-GraphApplication {
    $filter = [uri]::EscapeDataString("appId eq '$appRegistrationAppId'")
    $select = [uri]::EscapeDataString('id,appId,web')
    $payload = Invoke-GraphGetJson 'External ID app registration query' "https://graph.microsoft.com/v1.0/applications?`$filter=$filter&`$select=$select"
    $matches = @($payload.value)
    if ($matches.Count -ne 1) { throw "External ID app registration resolution returned $($matches.Count) objects; exactly one is required." }
    $application = $matches[0]
    if ([string]$application.appId -cne $appRegistrationAppId -or [string]::IsNullOrWhiteSpace([string]$application.id)) { throw 'External ID app registration resolution did not return the expected exact app/object.' }
    return $application
}

function Get-SupportedWebPayload {
    param([object]$Web)
    if ($null -eq $Web -or $null -eq $Web.PSObject.Properties['redirectUris']) { throw 'Graph web object is missing redirectUris.' }
    $redirectUris = @($Web.redirectUris | ForEach-Object { [string]$_ })
    if ($redirectUris.Count -eq 0) { throw 'Graph web object has no redirect URIs.' }
    # Graph v1 writable web fields only. Derived redirectUriSettings is retained
    # in the complete snapshot for verification, never sent in a PATCH body.
    return [pscustomobject][ordered]@{
        homePageUrl = $Web.homePageUrl
        logoutUrl = $Web.logoutUrl
        redirectUris = $redirectUris
        implicitGrantSettings = $Web.implicitGrantSettings
    }
}

function Convert-CompactJson {
    param([object]$Value)
    return ($Value | ConvertTo-Json -Depth 20 -Compress)
}

function Assert-NonRedirectWebFieldsPreserved {
    param([object]$BeforeWeb, [object]$AfterWeb)
    $before = Get-SupportedWebPayload $BeforeWeb
    $after = Get-SupportedWebPayload $AfterWeb
    foreach ($field in @('homePageUrl','logoutUrl','implicitGrantSettings')) {
        if ((Convert-CompactJson $before.$field) -cne (Convert-CompactJson $after.$field)) { throw "Graph web field $field changed during callback reduction." }
    }
}

function Assert-ExactWebSnapshot {
    param([object]$ExpectedWeb, [object]$ActualWeb)
    if ((Convert-CompactJson $ExpectedWeb) -cne (Convert-CompactJson $ActualWeb)) { throw 'Fresh Graph web snapshot does not exactly match the saved complete web object.' }
}

function Get-CanonicalSettingsSnapshot {
    $payload = Invoke-AzJson 'Sanitized canonical settings query' @('webapp','config','appsettings','list','--resource-group',$resourceGroup,'--name',$webAppName,'--query',"[?name=='PEERSLATE_CANONICAL_HOST' || name=='PEERSLATE_ENFORCE_CANONICAL_HOST'].{name:name,value:value}",'--output','json')
    $rows = if ($null -eq $payload) { @() } else { @($payload) }
    $names = @('PEERSLATE_CANONICAL_HOST','PEERSLATE_ENFORCE_CANONICAL_HOST')
    $values = @{}
    foreach ($row in $rows) {
        if ($null -eq $row.name -or $row.name -notin $names -or $values.ContainsKey([string]$row.name)) { throw 'Canonical settings query returned an invalid row.' }
        $values[[string]$row.name] = [string]$row.value
    }
    return [pscustomobject]@{
        settings = @(
            foreach ($name in $names) {
                [pscustomobject]@{ name = $name; present = $values.ContainsKey($name); value = if ($values.ContainsKey($name)) { $values[$name] } else { $null } }
            }
        )
    }
}

function Get-CallbackWebSnapshot {
    $application = Get-GraphApplication
    $web = $application.web
    Get-SupportedWebPayload $web | Out-Null
    return [pscustomobject]@{ web = $web }
}

function Assert-HeaderContract {
    param([string]$HeaderPath, [int]$ExpectedStatus, [string]$ExpectedLocation, [switch]$NoLocation)
    $headers = Get-Content -LiteralPath $HeaderPath -Raw
    if ($headers -notmatch "(?m)^HTTP/\S+ $ExpectedStatus\b") { throw "$HeaderPath did not return HTTP $ExpectedStatus." }
    if ($NoLocation) {
        if ($headers -match "(?im)^Location:") { throw "$HeaderPath unexpectedly includes a Location header." }
    } elseif ($headers -notmatch ("(?im)^Location:\s*" + [regex]::Escape($ExpectedLocation) + "\s*$")) {
        throw "$HeaderPath did not redirect to the fixed expected Location."
    }
}

Invoke-AzQuiet 'Subscription selection' @('account','set','--subscription',$subscriptionId)
$productionAuthPreflight = Invoke-AzJson 'Production Easy Auth External ID preflight' @('webapp','auth','show','--resource-group',$resourceGroup,'--name',$webAppName,'--query','{clientId:clientId,issuer:issuer}','--output','json')
if ([string]$productionAuthPreflight.clientId -cne $appRegistrationAppId) { throw 'Production Easy Auth clientId does not exactly match the pinned External ID app registration.' }
if ([string]$productionAuthPreflight.issuer -cne $expectedExternalIdIssuer) { throw 'Production Easy Auth issuer does not exactly match the pinned External ID issuer/tenant.' }
$productionAuthPreflightPath = Save-SanitizedJson ([pscustomobject]@{ clientId = [string]$productionAuthPreflight.clientId; issuer = [string]$productionAuthPreflight.issuer; tenantId = $entraTenantId }) 'external-id-auth-preflight.json'
$graphAccessToken = Get-ExternalIdGraphAccessToken
$graphHeaders = @{ Authorization = "Bearer $graphAccessToken" }
Remove-Variable graphAccessToken

# The current cutover has exactly two alternate aliases. Discover the direct
# Azure hostname rather than copying it from a previous release record, and
# fail before any mutation if either alias is not currently bound.
$hostnameInventory = Invoke-AzJson 'Production hostname inventory' @('webapp','show','--resource-group',$resourceGroup,'--name',$webAppName,'--query','{defaultHostName:defaultHostName,hostNames:hostNames}','--output','json')
$directAzureHostname = [string]$hostnameInventory.defaultHostName
$boundHostNames = @($hostnameInventory.hostNames | ForEach-Object { [string]$_ })
if ([string]::IsNullOrWhiteSpace($directAzureHostname)) { throw 'Production hostname inventory has no default hostname.' }
$currentCutoverAliases = @($directAzureHostname, 'pete.peerslate.com')
if ((@($currentCutoverAliases | Sort-Object -Unique).Count -ne 2)) { throw 'Current cutover alias inventory is not exactly two distinct aliases.' }
$expectedBoundHostNames = @('peerslate.com', $directAzureHostname, 'pete.peerslate.com')
if (($boundHostNames | Sort-Object -Unique).Count -ne $boundHostNames.Count -or $boundHostNames.Count -ne $expectedBoundHostNames.Count -or (Compare-Object -ReferenceObject ($expectedBoundHostNames | Sort-Object) -DifferenceObject ($boundHostNames | Sort-Object))) { throw 'Production App Service bindings are not exactly the approved apex, direct Azure hostname, and pete.peerslate.com set; stop before mutation.' }
$wwwHostname = 'www.peerslate.com'
if ($boundHostNames -contains $wwwHostname) { throw 'www.peerslate.com is outside the approved cutover scope; stop and obtain new authority.' }
$aliasInventoryBeforePath = Save-SanitizedJson ([pscustomobject]@{
    directAzureHostname = $directAzureHostname
    currentCutoverAliases = $currentCutoverAliases
    boundHostNames = $boundHostNames
    www = [pscustomobject]@{ hostname = $wwwHostname; appServiceBound = $false; currentCutoverScope = $false }
}) 'canonical-alias-inventory-before.json'

# Sanitized before snapshots: never request a full app-settings listing.
$canonicalBefore = Get-CanonicalSettingsSnapshot
$callbackWebBefore = Get-CallbackWebSnapshot
$callbacksBefore = @($callbackWebBefore.web.redirectUris | ForEach-Object { [string]$_ })
$expectedCallbacksBefore = @($approvedApexCallback, "https://$directAzureHostname/.auth/login/aad/callback", 'https://pete.peerslate.com/.auth/login/aad/callback')
if (($callbacksBefore | Sort-Object -Unique).Count -ne $callbacksBefore.Count -or $callbacksBefore.Count -ne $expectedCallbacksBefore.Count -or (Compare-Object -CaseSensitive -ReferenceObject ($expectedCallbacksBefore | Sort-Object) -DifferenceObject ($callbacksBefore | Sort-Object))) { throw 'Entra callbacks are not exactly the approved apex, direct Azure hostname, and pete.peerslate.com set with exact casing; stop before mutation.' }
if (@($callbacksBefore | Where-Object { $_ -match '^https://www\.peerslate\.com/' }).Count -ne 0) { throw 'www.peerslate.com has an Entra callback outside the approved cutover scope; stop and obtain new authority.' }
$canonicalBeforePath = Save-SanitizedJson $canonicalBefore 'canonical-settings-before.json'
$callbackWebBeforePath = Save-SanitizedJson $callbackWebBefore 'callback-web-before.json'
$callbacksBeforePath = Save-SanitizedJson ([pscustomobject]@{ callbackCount = $callbacksBefore.Count; redirectUris = $callbacksBefore }) 'callbacks-before-sanitized.json'
~~~

After the merged artifact is deployed with enforcement still false, enable only
the canonical settings. Output none avoids a full app-settings payload.

~~~powershell
Invoke-AzQuiet 'Canonical settings enablement' @('webapp','config','appsettings','set','--resource-group',$resourceGroup,'--name',$webAppName,'--settings','PEERSLATE_CANONICAL_HOST=peerslate.com','PEERSLATE_ENFORCE_CANONICAL_HOST=true','--output','none')
$canonicalAfter = Get-CanonicalSettingsSnapshot
if (-not $canonicalAfter.settings[0].present -or $canonicalAfter.settings[0].value -ne 'peerslate.com' -or -not $canonicalAfter.settings[1].present -or $canonicalAfter.settings[1].value -ne 'true') { throw 'Canonical settings did not persist the requested exact values.' }
$canonicalAfterPath = Save-SanitizedJson $canonicalAfter 'canonical-settings-after.json'

foreach ($alias in $currentCutoverAliases) {
    $headPath = Join-Path $evidenceDirectory "$alias-head.txt"
    $getPath = Join-Path $evidenceDirectory "$alias-get.txt"
    $postPath = Join-Path $evidenceDirectory "$alias-unsafe-post.txt"
    Invoke-CurlHeaders "$alias HEAD" @('--silent','--show-error','--head',"https://$alias/app") $headPath
    Assert-HeaderContract $headPath 308 'https://peerslate.com/app'
    Invoke-CurlHeaders "$alias GET" @('--silent','--show-error',"https://$alias/auth/sign-in?return_to=/app") $getPath
    Assert-HeaderContract $getPath 308 'https://peerslate.com/auth/sign-in?return_to=/app'
    Invoke-CurlHeaders "$alias unsafe POST" @('--silent','--show-error','--request','POST',"https://$alias/auth/sign-out") $postPath
    Assert-HeaderContract $postPath 400 $null -NoLocation
}
~~~

Only after both dynamically enumerated, bound aliases pass those checks may the
operator reduce callbacks. The Graph PATCH is derived from the complete saved
web object but sends only its four v1-writable fields, changing only
`redirectUris`. A fresh Graph GET must first match the saved complete `web`
object exactly, preventing an intervening callback drift from being overwritten;
after PATCH it must prove both the exact URI reduction and preservation of every
other supported web field.

~~~powershell
$reductionApplication = Get-GraphApplication
$callbackWebBeforeReduction = [pscustomobject]@{ web = $reductionApplication.web }
Assert-ExactWebSnapshot $callbackWebBefore.web $callbackWebBeforeReduction.web
$reductionWeb = Get-SupportedWebPayload $callbackWebBeforeReduction.web
$reductionWeb.redirectUris = @($approvedApexCallback)
Invoke-GraphPatchNoContent 'Callback reduction PATCH' "https://graph.microsoft.com/v1.0/applications/$($reductionApplication.id)" ([pscustomobject]@{ web = $reductionWeb })
$callbackWebAfter = Get-CallbackWebSnapshot
$callbacksAfter = @($callbackWebAfter.web.redirectUris | ForEach-Object { [string]$_ })
if ($callbacksAfter.Count -ne 1 -or $callbacksAfter[0] -cne $approvedApexCallback) { throw 'Callback reduction did not leave exactly the approved apex callback.' }
Assert-NonRedirectWebFieldsPreserved $callbackWebBefore.web $callbackWebAfter.web
$callbacksAfterPath = Save-SanitizedJson ([pscustomobject]@{ callbackCount = $callbacksAfter.Count; redirectUris = $callbacksAfter }) 'callbacks-after-sanitized.json'
~~~

## Exact rollback order

If callback reduction has occurred, restore the callback web object first from
the protected operator-local callback-web-before.json snapshot. Stop unless
the tenant-scoped Graph PATCH succeeds and a fresh full `web` query exactly
matches the saved complete object (including a returned derived
`redirectUriSettings` collection). The rollback payload contains only the four
Graph v1-writable `web` fields; it never sends a derived or read-only field.
Only then restore the prior presence and value of both canonical settings; an
absent pre-cutover setting is deleted, not replaced with false. Restore the
previous artifact only after those route prerequisites are true.

~~~powershell
$callbackWebBefore = Convert-NativeJson 'Saved callback web snapshot' (Get-Content -LiteralPath $callbackWebBeforePath -Raw)
if ($null -eq $callbackWebBefore.web -or @($callbackWebBefore.web.redirectUris).Count -eq 0) { throw 'Saved callback web snapshot is invalid or empty; rollback stops.' }
$rollbackWeb = Get-SupportedWebPayload $callbackWebBefore.web
$rollbackApplication = Get-GraphApplication
Invoke-GraphPatchNoContent 'Callback web restore PATCH' "https://graph.microsoft.com/v1.0/applications/$($rollbackApplication.id)" ([pscustomobject]@{ web = $rollbackWeb })
$restoredCallbackWeb = Get-CallbackWebSnapshot
Assert-ExactWebSnapshot $callbackWebBefore.web $restoredCallbackWeb.web

$canonicalBefore = Convert-NativeJson 'Saved canonical settings snapshot' (Get-Content -LiteralPath $canonicalBeforePath -Raw)
if (@($canonicalBefore.settings).Count -ne 2) { throw 'Saved canonical settings snapshot is invalid; rollback stops.' }
$expectedCanonicalNames = @('PEERSLATE_CANONICAL_HOST','PEERSLATE_ENFORCE_CANONICAL_HOST')
$savedCanonicalNames = @($canonicalBefore.settings | ForEach-Object { [string]$_.name })
if (($savedCanonicalNames | Sort-Object -Unique).Count -ne 2 -or (Compare-Object -ReferenceObject ($expectedCanonicalNames | Sort-Object) -DifferenceObject ($savedCanonicalNames | Sort-Object))) { throw 'Saved canonical settings snapshot does not contain both required settings exactly once.' }
foreach ($entry in @($canonicalBefore.settings)) {
    if ($entry.name -notin @('PEERSLATE_CANONICAL_HOST','PEERSLATE_ENFORCE_CANONICAL_HOST') -or $entry.present -isnot [bool]) { throw 'Saved canonical settings snapshot has an invalid entry.' }
    if ($entry.present -and $null -eq $entry.value) { throw "Saved canonical settings snapshot has no value for present setting $($entry.name)." }
    if ($entry.present) {
        Invoke-AzQuiet "Restore $($entry.name)" @('webapp','config','appsettings','set','--resource-group',$resourceGroup,'--name',$webAppName,'--settings',"$($entry.name)=$($entry.value)",'--output','none')
    } else {
        Invoke-AzQuiet "Delete previously absent $($entry.name)" @('webapp','config','appsettings','delete','--resource-group',$resourceGroup,'--name',$webAppName,'--setting-names',$entry.name,'--output','none')
    }
}
$canonicalRestored = Get-CanonicalSettingsSnapshot
$savedCanonicalJson = ($canonicalBefore.settings | ConvertTo-Json -Depth 6 -Compress)
$restoredCanonicalJson = ($canonicalRestored.settings | ConvertTo-Json -Depth 6 -Compress)
if ($savedCanonicalJson -cne $restoredCanonicalJson) { throw 'Canonical settings do not exactly match the saved presence/value snapshot.' }
$canonicalRestoredPath = Save-SanitizedJson $canonicalRestored 'canonical-settings-restored.json'

# If application behavior also requires it, restore the previous known-good
# artifact through the normal Azure release path only after the checks above.
~~~

Then verify /healthz, signed-out /app, /auth/sign-in, and the restored alias
behavior. Do not change DNS, Front Door, Conditional Access, Entra provider
settings, database configuration, session duration, or offline_access as an
ad hoc rollback substitute.
