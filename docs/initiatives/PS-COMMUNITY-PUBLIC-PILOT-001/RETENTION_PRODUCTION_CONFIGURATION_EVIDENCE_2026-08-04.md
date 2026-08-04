# Retention — production configuration evidence

- **Initiative:** `PS-COMMUNITY-PUBLIC-PILOT-001`
- **Evidence item:** 5 of the approved retention decision — "Verify the exact
  production Azure SQL short-term retention, absence of long-term retention,
  Blob soft-delete window, private container/RBAC, Defender scan behavior, and
  deletion-worker schedule."
- **Captured:** 2026-08-04, read-only `az` queries against live production.

## Result: the approved commitments are met

| Approved commitment | Production reality | Verdict |
|---|---|---|
| Azure SQL "7-day short-term recovery window" | `peerslate-database` retentionDays = **7** (12-hour differential interval) | **Matches** |
| "no long-term-retention copy for the Community pilot" | LTR weekly / monthly / yearly all `PT0S` — none configured | **Matches** |
| Blob "7-day soft-delete recovery window" | `peerslatecapturemedia` delete retention **enabled, 7 days**; container soft delete also enabled | **Matches** |
| "privately stored" attachments | container `peerslate-private-capture-media` publicAccess = **null** (private); account `allowBlobPublicAccess` = **false** | **Matches** |
| No shared-key access | `allowSharedKeyAccess` = **false** on both accounts — access is managed-identity only | **Exceeds** |
| Transport security | `minimumTlsVersion` = **TLS1_2** on both accounts | **Matches** |

The storage account Community attachments actually use was confirmed from
production configuration rather than assumed: `CAPTURE_MEDIA_BLOB_ACCOUNT_URL`
resolves to `peerslatecapturemedia.blob.core.windows.net`, and
`CAPTURE_MEDIA_BLOB_CONTAINER` to `peerslate-private-capture-media`.

## Two honest gaps

**1. Defender for Storage is on the Free tier.** The approved schedule's
malware-scan row assumes scanning exists ("Retain only the scan state and Blob
tags required to keep unsafe files unavailable"). The application's own narrow
safety contract still gates what can become public, and the media state
machine refuses to publish anything not marked `clean`, so an unscanned file
cannot reach a visitor. But *provider-side* malware scanning is not currently
paid for. This does not break the retention schedule; it means the row
describing scan metadata is currently describing application state, not
Defender state. Enabling Defender for Storage is a cost decision for Pete.

**2. `peerslatevoiceprod` has soft delete disabled.** This is a different
account from the one Community attachments use, so it does not affect the
commitment above. Community Voice is transient by design — a recording is
never stored as a Community attachment — so the practical exposure is low.
Flagged here because the overnight audit raised it and it should not be lost.

## Deletion-worker schedule

The last clause of evidence item 5 is satisfied by
`services/community_retention_service.py`: hourly content purge, daily audit
and outbox purge, on the request cadence, running only while the Community
flag is on. Its known limitation is recorded in the decision document — a site
with no visitors runs no purges, which is acceptable for the owner pilot and
should move to a timer-based worker if Community later serves real volume with
quiet periods.

## Commands used

Read-only. No production configuration was changed while capturing this.

```bash
az sql db str-policy show --resource-group peerslate --server peerslate --name peerslate-database
az sql db ltr-policy show --resource-group peerslate --server peerslate --name peerslate-database
az storage account blob-service-properties show --account-name peerslatecapturemedia --resource-group peerslate
az storage container show --account-name peerslatecapturemedia --name peerslate-private-capture-media --auth-mode login
az storage account list
az security pricing show --name StorageAccounts
```
