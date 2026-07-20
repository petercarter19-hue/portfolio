# PS-CAPTURE-MEDIA-001 - Shared Media Architecture

## Architectural chain

```text
server-resolved owner
  -> photo source row (private, uploading)
  -> opaque original Blob (private quarantine)
  -> Defender result (scanning / clean / unsafe / error)
  -> bounded server decode + metadata-stripped derivative
  -> owner review and authored note
  -> explicit transactional confirmation
  -> one dbo.captures row (capture_type = photo)
  -> one source-to-Capture link
  -> existing correction/archive/export/delete lifecycle
  -> optional later Moment proposal from an exact Capture version
```

The Capture row remains the convergence point. Binary source data and technical
provenance are not canonical Story/Moment content, and a media source is not a
second Capture.

## Data model

### `dbo.capture_media_sources`

One owner-scoped original source. The initial migration is structurally reusable
for `photo`, `document`, and `video`, but the first procedures accept `photo`
only. Required fields:

- internal ID and opaque `source_key`;
- `owner_profile_id` and creator/deleter actor IDs;
- `source_type` with a controlled enum;
- opaque original and derivative Blob names, nullable only in terminal deletion;
- verified original and derivative content types;
- original/derivative byte length and SHA-256 digest;
- trusted pixel width/height for photos;
- lifecycle state, scan result enum, safe error code, and relevant UTC times;
- confirmation/deletion timestamps and SQL `rowversion`.

It stores no member name, email, profile slug, client path, original filename,
EXIF/GPS value, Capture text, AI output, downstream destination, audience, or
publication payload. Blob names are server-generated under fixed type/version
prefixes and contain no owner or content data.

### `dbo.capture_media_links`

One owner-safe link from one media source to at most one Capture. Photo v1 is
one-to-one. The link records source, owner, Capture, confirming actor/time, and
the exact source state eligible at confirmation. It contains no copied Capture
body or media metadata.

### Existing `dbo.captures`

Explicit confirmation inserts one private, active `capture_type = photo` row
using the owner-authored reviewed note as immutable original body. Later changes
use PS-CAPTURE-002 revisions. Confirmation and link creation occur in one SQL
transaction and are idempotent for replay/concurrency.

No new Moment, Placement, destination, audience, access-grant, publication, or
projection table is introduced.

## Lifecycle

Photo v1 uses these explicit states:

1. `uploading` - SQL owner/source exists; original Blob is not yet proven.
2. `scanning` - original Blob exists and is inaccessible to member delivery.
3. `processing` - Defender reports clean; server is validating pixels and
   producing the safe derivative.
4. `needs_review` - safe preview is available to its owner; no Capture exists.
5. `confirmed` - one private photo Capture and one source link exist.
6. `failed` - upload, scan, or derivative processing needs a safe retry or
   replacement; no preview or Capture is exposed.
7. `rejected` - the file is unsafe, malformed, unsupported, or violates a hard
   bound; it cannot be confirmed or downloaded.
8. `deletion_pending` - SQL has committed deletion intent; Blob cleanup must
   complete before deletion is reported successful.
9. `deleted` - original/derivative locators, digests, dimensions, and any draft
   content are cleared; only a body-free lifecycle tombstone remains.

There is no transition from `scanning`, `failed`, or `rejected` directly to a
Capture. State changes require expected row-version tokens.

## Service boundaries

- `photo_capture_service.py` coordinates validation, SQL transitions, scan
  result reconciliation, normalization, confirmation, authorized retrieval,
  and distributed deletion.
- `capture_media_storage_service.py` accepts only fixed server-owned account and
  container configuration plus opaque `photo/v1/...` names. It never accepts a
  URL, credential, account, container, or path from the request.
- Existing `media_storage_service.py` and `voice_capture_service.py` remain
  Voice-owned and behaviorally unchanged.
- The Capture route uses a generic lifecycle dispatcher for delete/export so
  text, Voice, and photo retain their own source cleanup while presenting one
  Capture contract.
- Database calls remain in the stored-procedure allowlist. Procedures resolve
  the owner from the server-provided user key inside SQL.

## Scan and normalization decision

1. Before storage, the server enforces bounded bytes, a JPEG/PNG MIME allowlist,
   and minimal signature checks.
2. The original is written once to the quarantine container with no member
   metadata and no overwrite.
3. Defender for Storage scans the committed block Blob. Until a known-clean
   result is reconciled, all preview, download, export-byte, and confirmation
   paths fail closed.
4. The application reads scan status through a least-privilege custom role that
   grants only Blob-tag read in addition to its container-scoped data role. It
   never receives tag-write permission.
5. A clean tag is not the only control. The service verifies the original Blob
   against the stored byte count/digest, opens only allowlisted formats with
   Pillow, treats decompression-bomb warnings as errors, checks dimensions,
   applies orientation, loads pixels, and writes a new derivative without EXIF,
   GPS, comments, profiles, or client filename.
6. Only the derivative is used for in-product preview or future projection.
   The clean original is available only through an owner-authorized explicit
   download/export action.

Pillow's current security guidance specifically calls for an image-format
allowlist and enforced decompression-bomb limits. The implementation writer
must pin the reviewed version and record its dependency/security impact:
<https://pillow.readthedocs.io/en/stable/handbook/security.html>.

## Provenance and member authority

- The original Blob and its digest preserve exact private source evidence after
  a clean result.
- The safe derivative records its own digest, dimensions, and content type; it
  is a derived representation, never the original.
- The owner-authored note is the Capture's original body. No OCR or AI text is
  generated in Photo v1.
- Later Capture corrections do not change source bytes.
- Later Moment creation pins an exact Capture version through the existing
  contract; it does not read image bytes automatically.

## Idempotency and concurrency

- A unique opaque source key identifies one upload lifecycle. Upload retry after
  uncertain Blob success first proves whether the exact opaque Blob exists and
  matches expected properties; it never overwrites.
- Scan reconciliation is repeatable. Re-reading the same clean/unsafe/error
  result does not duplicate derivative work or audit events.
- Confirmation locks source/link/Capture decisions in a documented order and
  creates at most one Capture for one source.
- Delete is retryable across SQL and two Blobs. A partial Blob failure remains
  `deletion_pending`; the UI never reports deletion complete early.

## Compatibility rule

The photo migration must preserve the complete result shape and behavior of the
current Capture/Voice procedures. Existing text and Voice unit, integration,
export, correction, archive/restore, Moment, and deletion tests are mandatory
regressions. Any implementation that requires changing Voice source tables,
Speech behavior, or accepted UI stops for manager review.
