# PS-CAPTURE-MEDIA-001 - Current-State Inventory

_Inventory date: 2026-07-19. Authority: fetched Azure DevOps `origin/main` at
`229bfba4cd31e0eb56b99a94e90f16aa3fabb396`._

## What is already real and reusable

| Foundation | Current contract | Reuse rule |
| --- | --- | --- |
| Identity | PS-AUTH-001 resolves the signed-in user on the server and supports two-owner isolation. | Every media operation starts from server identity; clients never submit an owner/profile ID. |
| Text Capture | `dbo.captures` already allows `text`, `voice`, `photo`, `video`, and `document`; create/list, corrections, archive/restore, export, and explicit deletion are live. | Photo converges on one `capture_type = photo` row only after explicit save. No parallel canonical Capture model. |
| Capture lifecycle | PS-CAPTURE-002 preserves immutable original text plus revisions and uses row-version concurrency and body-free deletion tombstones. | Photo note corrections use the same revision history. Archive retains the private source; delete removes source bytes before success. |
| Moment | PS-MOMENT-001 pins one exact Capture original/revision, creates an editable private proposal, and requires explicit confirmation. | Photo save never creates a Moment. The existing action may later create a proposal from the exact photo Capture version. |
| Placement | PS-PLACEMENT-001 stores a body-free reference from one exact confirmed Moment version to one eligible private destination. | Photo does not create, display, or consume a placement. |
| Voice | PS-VOICE-001 provides private Blob storage, managed identity, opaque paths, owner-authorized playback/download, immutable source provenance, retry states, explicit save, export, and distributed deletion. | Reuse the contracts and lessons. Do not change `dbo.voice_*`, Speech, Voice paths, or the accepted Speak/Type behavior. |
| Protected Capture UI | `/app/capture` has accepted responsive Speak/Type and review states. Photo/video/document appear as truthful disabled `Coming later` scaffolding. | The real Voice/Type product is the upstream visual minimum. Photo-specific states need a V1 acceptance package before frontend implementation. |

## Repository implementation facts

- `SQL FIles/Migrations/proposed/PS-CAPTURE-001_captures.sql` already permits a
  `photo` Capture type; no Capture-type constraint expansion is needed.
- `services/media_storage_service.py` is intentionally Voice-only: its accepted
  blob-name regex, container settings, and errors are scoped to `voice/v1`.
- `services/voice_capture_service.py` owns Voice upload, transcription,
  confirmation, authorized audio retrieval, and retryable Blob-first deletion.
- `PS-VOICE-001_voice_capture.sql` currently extends the shared Capture
  list/delete/export procedures for Voice. Photo must extend those shared
  procedures again without regressing text or Voice results.
- `owner_routes.py` currently routes generic Capture deletion through the Voice
  lifecycle orchestrator because Voice was the first binary source. The photo
  backend package must introduce a generic dispatch boundary while keeping all
  existing text/Voice outcomes and tests unchanged.
- The production dependency set has Azure Identity and Blob SDK support, but no
  image decoder/normalizer. A reviewed, pinned Pillow dependency is required for
  strict format decoding, pixel limits, orientation handling, and creation of a
  metadata-stripped preview derivative.

## Production evidence

Repository governance records:

- Capture lifecycle: PR 63 / pipeline 85.
- Moment: PR 66 / pipeline 91.
- Placement: PR 68 / pipeline 93.
- accepted protected Voice correction: PR 80 / pipeline 113, followed by
  governance closeout PR 81 / pipeline 115.

A credential-safe, read-only Azure control-plane check on 2026-07-19 found:

- one existing Voice GPv2 account, `peerslatevoiceprod`;
- Blob public access disabled;
- shared-key access disabled;
- minimum TLS 1.2; and
- Defender for Storage and on-upload malware scanning disabled on that account.

No App Service setting values, member media, Blob contents, database content,
credentials, or secrets were read.

## Infrastructure conclusion

The existing Voice account proves the private Blob/managed-identity pattern,
but it is not the correct physical home for the new file-upload pipeline.
Enabling account-level scanning or malicious-blob soft deletion there could
change Voice cost and deletion semantics. The selected architecture therefore
uses a separate Capture Media GPv2 account for photo/document/video sources,
with its own scan policy, cost cap, retention controls, and container-scoped
managed-identity access. Voice remains untouched.

Microsoft documents on-upload scanning as the fit for user-generated uploads,
with variable completion time and per-GB billing/caps. It also warns that Blob
index tags should not be the only security control. The photo design therefore
fails closed while scanning, verifies a clean result through least-privilege
server access, then independently decodes and re-encodes a safe derivative:

- <https://learn.microsoft.com/en-us/azure/defender-for-cloud/on-upload-malware-scanning>
- <https://learn.microsoft.com/en-us/azure/defender-for-cloud/introduction-malware-scanning>

## Current gaps

- No photo/video/document source schema, route, service, provider, visual-state
  package, test evidence, implementation branch, PR, deployment, or live proof
  exists.
- No production upload-scanning service is enabled for Capture Media.
- No safe photo derivative pipeline or photo export/deletion contract exists.
- No approved photo-specific desktop/mobile/error-state design exists.
- Homepage attachments still truthfully say `Coming later`; parity will become
  open when the protected photo experience materially changes.
