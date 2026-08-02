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
Every JSON response is captured first, checked for native success, parsed and
validated, then written as evidence.

~~~powershell
$ErrorActionPreference = 'Stop'

$subscriptionId = '<AZURE_SUBSCRIPTION_ID>'
$resourceGroup = '<WEBAPP_RESOURCE_GROUP>'
$webAppName = '<WEBAPP_NAME>'
$appRegistrationAppId = '<APP_REGISTRATION_CLIENT_ID>'
$approvedApexCallback = '<APPROVED_APEX_CALLBACK_URI>'
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

function Invoke-AzText {
    param([string]$Label, [string[]]$Arguments)
    $raw = & az @Arguments
    if ($LASTEXITCODE -ne 0) { throw "$Label failed with exit code $LASTEXITCODE." }
    $text = ($raw | Out-String).Trim()
    if ([string]::IsNullOrWhiteSpace($text)) { throw "$Label returned no value." }
    return $text
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
    $payload = Invoke-AzJson 'Callback web query' @('ad','app','show','--id',$appRegistrationAppId,'--query','{web:web}','--output','json')
    if ($null -eq $payload.web -or @($payload.web.redirectUris).Count -eq 0) { throw 'Callback web object is absent or has no redirect URIs.' }
    return $payload
}

function Get-CallbackUris {
    $payload = Invoke-AzJson 'Callback URI query' @('ad','app','show','--id',$appRegistrationAppId,'--query','{redirectUris:web.redirectUris}','--output','json')
    if ($null -eq $payload.redirectUris) { throw 'Callback URI query returned no redirectUris collection.' }
    return @($payload.redirectUris | ForEach-Object { [string]$_ })
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

# Sanitized before snapshots: never request a full app-settings listing.
$canonicalBefore = Get-CanonicalSettingsSnapshot
$callbackWebBefore = Get-CallbackWebSnapshot
$callbacksBefore = @($callbackWebBefore.web.redirectUris | ForEach-Object { [string]$_ })
if ($callbacksBefore.Count -eq 0 -or $callbacksBefore -notcontains $approvedApexCallback) { throw 'The nonempty callback web object does not include the exact approved apex callback.' }
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

$aliases = @('www.peerslate.com', '<AZURE_WEBAPP_HOSTNAME>', 'pete.peerslate.com')
foreach ($alias in $aliases) {
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

Only after those checks pass may the operator reduce callbacks. The fresh
sanitized query must prove that exactly one URI remains and that it is the
approved apex callback.

~~~powershell
Invoke-AzQuiet 'Callback reduction' @('ad','app','update','--id',$appRegistrationAppId,'--web-redirect-uris',$approvedApexCallback,'--output','none')
$callbacksAfter = Get-CallbackUris
if ($callbacksAfter.Count -ne 1 -or $callbacksAfter[0] -cne $approvedApexCallback) { throw 'Callback reduction did not leave exactly the approved apex callback.' }
$callbacksAfterPath = Save-SanitizedJson ([pscustomobject]@{ callbackCount = $callbacksAfter.Count; redirectUris = $callbacksAfter }) 'callbacks-after-sanitized.json'
~~~

## Exact rollback order

If callback reduction has occurred, restore the callback web object first from
the protected operator-local callback-web-before.json snapshot. Stop unless
the Graph PATCH succeeds and a fresh callback query exactly matches the saved
set. Only then restore the prior presence and value of both canonical settings;
an absent pre-cutover setting is deleted, not replaced with false. Restore the
previous artifact only after those route prerequisites are true.

~~~powershell
$callbackWebBefore = Convert-NativeJson 'Saved callback web snapshot' (Get-Content -LiteralPath $callbackWebBeforePath -Raw)
if ($null -eq $callbackWebBefore.web -or @($callbackWebBefore.web.redirectUris).Count -eq 0) { throw 'Saved callback web snapshot is invalid or empty; rollback stops.' }
$savedCallbacks = @($callbackWebBefore.web.redirectUris | ForEach-Object { [string]$_ })
$appObjectId = Invoke-AzText 'App object ID query' @('ad','app','show','--id',$appRegistrationAppId,'--query','id','--output','tsv')

Invoke-AzQuiet 'Callback web restore PATCH' @('rest','--method','PATCH','--uri',"https://graph.microsoft.com/v1.0/applications/$appObjectId",'--headers','Content-Type=application/json','--body',"@$callbackWebBeforePath",'--output','none')
$restoredCallbacks = Get-CallbackUris
if ($restoredCallbacks.Count -ne $savedCallbacks.Count -or (Compare-Object -ReferenceObject ($savedCallbacks | Sort-Object) -DifferenceObject ($restoredCallbacks | Sort-Object))) { throw 'Fresh callback query does not exactly match saved callbacks; canonical settings are untouched.' }

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
