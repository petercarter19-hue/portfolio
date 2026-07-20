# PS-CAPTURE-MEDIA-001 - Schema, Infrastructure, and Rollout

## SQL migration impact

`PS-CAPTURE-PHOTO-BACKEND-001` adds one forward migration, verifier, and guarded
rollback for:

- `dbo.capture_media_sources`;
- `dbo.capture_media_links`;
- owner-resolving source create/fail/status/reconcile/get/confirm/delete
  procedures;
- photo-aware extensions to shared Capture list/get/delete/export behavior; and
- migration ledger/fingerprint guards consistent with Capture, Voice, Moment,
  and Placement packages.

The migration does not alter the existing `CK_captures_type` because `photo` is
already allowed. It does not modify `dbo.voice_media_sources`,
`dbo.voice_transcription_attempts`, or `dbo.voice_capture_links`.

Composite owner-safe foreign keys, unique source/link keys, row-version tokens,
state checks, live/deleted payload checks, and idempotent confirmation are
database-enforced. Shared-procedure changes must retain the exact text/Voice
result contract and be protected by definition fingerprints.

## Application impact

New modules:

- `services/capture_media_storage_service.py`
- `services/photo_capture_service.py`
- optional narrow `services/capture_lifecycle_service.py` for generic
  text/Voice/photo deletion dispatch

Existing files requiring bounded changes:

- `services/database_service.py` for procedure allowlist only;
- `owner_routes.py` for feature-flagged photo endpoints and generic lifecycle
  dispatch;
- `requirements.txt` for a pinned Pillow dependency;
- `.env.example` for nonsecret account/container/limit/flag names;
- SQL migration runner and focused tests.

The backend branch adds no production-visible Photo control. Every photo route
fails closed while `CAPTURE_PHOTO_ENABLED` is false.

## Dependency decision

Photo v1 requires Pillow for full image decode, format allowlisting, dimension
and decompression-bomb enforcement, orientation correction, resizing, and a new
metadata-stripped derivative. MIME/magic checks alone cannot provide those
guarantees.

Impact:

- adds native image libraries and a security patch obligation;
- increases CPU/memory use for accepted images;
- requires hard byte/pixel/dimension bounds and warnings-as-errors;
- requires dependency/advisory review and CI install proof; and
- must not execute on unscanned input or expand beyond JPEG/PNG.

The implementation writer pins the then-current reviewed release (Pillow 12.3.0
is current at planning time), records transitive binaries, and stops if the
production build image cannot install it predictably.

## Azure infrastructure decision

Create a separate, globally unique GPv2 Capture Media account in the existing
`peerslate` resource group. Exact global name is selected and recorded by the
implementation writer's plan output; it must not be guessed into application
code. Required controls:

- Standard_LRS unless a current availability/data-residency review requires
  otherwise;
- HTTPS only, TLS 1.2 minimum, Blob public access off, shared key off;
- one private `peerslate-private-capture-media` container;
- App Service managed identity with container-scoped Blob Data Contributor;
- custom container-scoped role with Blob index-tag **read only**;
- Defender for Storage enabled at the account level;
- on-upload malware scanning enabled with initial 10 GB/month cap;
- scan-result tags enabled; malicious-blob soft-delete remediation enabled with
  seven-day retention;
- alerts/evidence for 75%/100% cap, scan failures, and malicious detection; and
- only nonsecret application settings for account URL, container, limits,
  derivative dimensions, and feature flag.

Do not list/read App Service settings during verification. Known values are
proved by the signed-in lifecycle after deploy, following the Voice precedent.

## Infrastructure script

Add `scripts/provision_capture_media_azure.ps1` with explicit `plan`, `apply`,
and `verify` modes. `plan` is nonmutating. `apply` requires a confirmation switch
and reviewed resource names, suppresses provider output, creates no key/SAS,
and makes no production SQL change. `verify` checks resource posture, Defender
state/cap/remediation, container privacy, and exact managed-identity roles
without reading credentials or setting values.

Azure documents tag-read as a separate permission; do not solve it by granting
the broad built-in Blob Data Owner role:
<https://learn.microsoft.com/en-us/azure/storage/blobs/storage-blob-index-how-to>.

## Release sequence

1. **Manager gate:** merge this accepted architecture package.
2. **Backend branch:** implement schema/services/routes default-off, complete
   diff review, focused/full tests, and isolated SQL/Blob/Defender proof.
3. **Backend acceptance:** designated manager accepts `Pass` evidence; writer
   opens Azure PR, squash-merges, and verifies normal pipeline with flag off.
4. **Production foundation:** manager approves reviewed infrastructure plan;
   writer applies/verifies the new account and Defender controls, then applies
   and verifies SQL through the configured secure pipeline path. No member file
   is used.
5. **Visual V1 gate:** Pete and manager accept every photo desktop/mobile/error
   state before runtime frontend work.
6. **Frontend branch:** Claude Code integrates the accepted design with the real
   backend, keeps the feature off, self-reviews, and supplies visual/functional
   evidence.
7. **Product acceptance:** Pete and manager accept the real protected desktop
   and mobile experience.
8. **Release:** frontend writer completes Azure PR/pipeline/deploy, enables the
   reviewed flag, runs signed-in synthetic lifecycle and auth-boundary checks,
   and records exact evidence.
9. **Homepage parity:** release and verify the exact downstream homepage
   projection package in the same wave before Capture Media is declared closed.
10. **Governance closeout:** reserve and update shared baseline/state/active
    pointers with exact PR, SHA, pipeline, production, visual, and parity proof.

## Rollback

- Immediate application rollback: disable `CAPTURE_PHOTO_ENABLED`; retain
  owner-authorized review/export/delete endpoints for already stored private
  data through a maintenance-safe path.
- Frontend rollback: revert/hide Photo entry without altering text/Voice.
- SQL rollback before any photo row exists: guarded rollback may remove only
  photo-media artifacts after procedure fingerprints and later dependencies
  match.
- SQL rollback after any row exists: refuse destructive rollback. Use a later
  preservation migration; never orphan Blobs or erase data rights.
- Infrastructure rollback before data: delete only the exact isolated/proven
  resources after absolute target verification.
- Infrastructure after data: do not delete the account/container or remove
  identity access needed for export/deletion. Disable intake and preserve the
  lifecycle until an approved migration completes.

## Cost and operational boundary

This plan intentionally adds a new Storage account and paid Defender for
Storage scanning. Storage bytes/transactions, Defender account protection,
per-GB scan, Blob index, and remediation retention can incur charges. The 10
GB/month cap and 10 unconfirmed-draft limit bound the first launch, but the cap
is not a security bypass and may have provider-documented deviation. Acceptance
of this manager package accepts that cost envelope; the implementation report
must record the live pricing review and plan output before production apply.
