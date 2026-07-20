# PS-CAPTURE-MEDIA-001 - Security, Privacy, and Lifecycle

## Authorization before storage and retrieval

- Resolve the active owner from the authenticated server session before
  creating a source row or Blob.
- Browser payloads never contain an accepted owner/profile/user ID, storage
  account, container, Blob name, URL, or authorization token.
- Every SQL procedure resolves ownership from the server-provided user key.
- Every preview, status, retry, original download, export, confirmation, and
  deletion operation proves source ownership before returning protected state
  or touching Blob storage.
- Cross-owner and absent opaque keys produce the same neutral result and no
  storage access. Timing-sensitive/concurrent tests must prove this boundary.

## Storage controls

- Use a separate GPv2 Capture Media account with secure transfer, minimum TLS
  1.2, public Blob access disabled, shared-key access disabled, no public
  container, and no browser credential/SAS path.
- The App Service managed identity receives Blob contributor access only at the
  new private container plus a custom role limited to Blob-tag read. Do not
  grant `Storage Blob Data Owner`, account keys, tag-write, or account-wide data
  access to the application.
- Original and derivative names are random, server-generated, versioned, and
  type-scoped. Upload uses `overwrite=False` and no member metadata.
- All app-mediated media responses use authorization first, bounded content
  length, a server-selected content type/filename, `Cache-Control: private,
  no-store`, `X-Content-Type-Options: nosniff`, and no public locator.

## Layered untrusted-file controls

1. Bounded request body and per-owner draft limit.
2. MIME and magic/signature allowlist before storage.
3. Private quarantine with no delivery while scan is unknown.
4. Defender for Storage on-upload malware scanning.
5. Fail closed for `Malicious`, `Error`, `Not scanned`, timeout, cap exhaustion,
   unavailable provider, absent tag, or unexpected result.
6. Stored byte-length/digest/ETag consistency check after a clean result.
7. Pillow format allowlist, full pixel load, decompression-bomb warning as
   error, dimension/pixel bounds, and new metadata-free derivative.
8. Only the derivative is used for product preview/projection.

Blob index tags are not treated as authorization and are not the only safety
control. The app cannot write them. A known-clean result enables independent
content decoding; it does not bypass owner authorization or format validation.

## Defender behavior and cost safety

- Enable Defender for Storage on the new Capture Media account only, with
  on-upload scanning and a manager-selected initial 10 GB/month scan cap.
- Because Microsoft notes that caps can be exceeded by a bounded deviation and
  that scanning stops after the cap, cap exhaustion is an operational alert and
  a fail-closed product state, not permission to accept unscanned files.
- Enable malicious-blob remediation/soft deletion on the new account with a
  seven-day recovery window. This does not touch Voice deletion semantics.
- Record provider result/time and a safe reason code in SQL; never copy provider
  payloads, file bytes, EXIF, client filename, or member content into logs/audit.
- Alert at 75% and 100% of the scan cap, on scan errors/timeouts, repeated
  processing failures, deletion backlog, and unexpected cross-owner outcomes.

Relevant current Microsoft behavior and cost controls are documented at:
<https://learn.microsoft.com/en-us/azure/defender-for-cloud/on-upload-malware-scanning>
and
<https://learn.microsoft.com/en-us/azure/defender-for-cloud/defender-for-storage-configure-malware-scan>.

## Data minimization and provenance

Persist only what is needed to prove owner, type, storage object, byte/digest
integrity, trusted dimensions, derivative relation, scan/lifecycle state,
actors/times, concurrency, and the source-to-Capture link. Do not persist:

- original filename or client path;
- EXIF, GPS, camera make/model, thumbnail, comments, color-profile contents, or
  detected faces/objects;
- content in Blob names/metadata, audit metadata, logs, route parameters, or
  provider correlation;
- OCR, embeddings, tags, moderation labels, generated descriptions, or inferred
  facts; or
- destination, audience, share, public, matching, or publication state.

## Failure and recovery matrix

| Failure | Persisted truth | Member action | Forbidden behavior |
| --- | --- | --- | --- |
| Client/network ends before accepted upload | No success claim; source may be absent or `uploading`. | Retry selection; server reconciles opaque source safely. | Overwrite an uncertain Blob or create a Capture. |
| Blob upload fails | `failed` with safe code or recoverable `uploading`. | Retry or delete. | Log provider response/blob path or report success. |
| Scan pending | `scanning`. | Wait, refresh status, use Type/Voice, or delete. | Preview, download, normalize, or confirm. |
| Scan malicious | `rejected`; provider remediation starts. | Choose another file or use Type/Voice. | Return bytes, disclose malware signature detail, or allow retry of the same source. |
| Scan error/not scanned/cap reached | `failed` with neutral safe code. | Retry scan through the approved recovery path, replace, or delete. | Treat absence of a bad result as clean. |
| Decode/dimension failure | `rejected` or `failed` by retryability. | Replace or delete. | Render original bytes in browser. |
| Derivative upload fails | `failed`; clean original remains private. | Retry processing or delete. | Confirm without a safe derivative. |
| Stale review/save | State unchanged. | Refresh review and submit current token. | Last-write-wins or duplicate Capture. |
| First Blob deletion succeeds, second fails | `deletion_pending`. | Retry; background/owner path continues cleanup. | Clear SQL locators or report deleted early. |
| Database unavailable after Blob write | Stable source URL and recovery state when known. | Resume/retry/delete after recovery. | Orphan without reconciliation evidence. |

## Deletion order

1. Owner-resolving SQL procedure locks source/Capture/link, validates row
   version, writes `deletion_pending`, and returns only trusted opaque Blob
   locators to the server.
2. The server deletes the derivative and original and verifies absence (or an
   accepted provider-remediated state). Retries are idempotent.
3. Final owner-resolving procedure clears Blob names, content types, lengths,
   digests, dimensions, scan detail, and any draft content; removes the link;
   applies the existing Capture aggregate deletion/tombstone behavior when
   relevant; then reports success.
4. Audit records contain event, opaque IDs, state, and time only.

Archive never deletes media. Draft deletion never touches another Capture.
Capture deletion never deletes a confirmed Moment; existing Moment source-
deleted behavior remains authoritative.

## Security stop conditions

Stop and return to the manager if implementation would:

- reuse the Voice account in a way that changes Voice scan, cost, retention, or
  deletion behavior;
- grant a browser Blob credential/URL or accept a client storage path;
- grant the app broad Storage Blob Data Owner/tag-write rights;
- make unscanned/original bytes retrievable from the server or treat the
  browser's explicitly labeled, device-local selection preview as a clean
  server preview;
- parse unsupported active formats or process images without hard byte/pixel
  limits;
- add OCR/AI/moderation/publication or collect EXIF/GPS;
- weaken same-origin, owner, row-version, or deletion-finalization checks; or
- require secrets, production member content, or direct `main` writes.
