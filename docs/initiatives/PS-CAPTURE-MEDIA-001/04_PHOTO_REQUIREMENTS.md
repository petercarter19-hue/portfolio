# PS-CAPTURE-MEDIA-001 - Photo v1 Requirements

## Member outcome

A signed-in member can take or choose one supported photo, let PeerSlate make a
private safe preview, write or edit what the photo means, and explicitly save
one private Capture. Nothing else is created or shared.

## Entry and validation

1. Keep **Type** and **Speak** first-class and fully usable. Add **Photo** as an
   equally understandable input, not as a replacement or a hidden submenu.
2. Offer separate **Take photo** and **Choose photo** labels on supported
   devices. Both use normal accessible file inputs; camera capture is a hint,
   never the only path.
3. Accept one JPEG or PNG. Reject empty, truncated, mislabeled, polyglot,
   unsupported, animated, or multiple files.
4. Enforce 10 MiB, 20 megapixels, and 8,192 pixels per edge on the server. Do
   not silently truncate or downscale the preserved original.
5. Never persist or log the original filename, filesystem path, EXIF values,
   browser device name, or owner identity in Blob metadata/path.
6. Resolve the authenticated owner and create the owner-scoped source record
   before the trusted server writes a Blob.

## Upload, scan, and processing

1. The browser shows selected-file type/size guidance and a local preview only
   while clearly labeling it **Not saved yet**. The local object URL is revoked
   when no longer needed and is never treated as server proof.
2. The server returns a stable opaque review URL after accepting the private
   original. It never returns the Blob locator or a SAS URL.
3. While Defender has not returned a known-clean result, show **Scanning your
   private photo** and keep preview/download/save unavailable.
4. A clean result starts bounded normalization. The final server preview is
   orientation-corrected and metadata-stripped, with a maximum 2,400-pixel long
   edge. It is not presented as the original.
5. Scan timeout/error and processing failure preserve a private recoverable
   source state when safe. The member may retry status/processing or delete the
   draft. An unsafe/rejected source cannot be previewed, downloaded, or saved as
   a Capture through the product path.
6. Type and Voice remain available during every photo failure.

## Review and explicit save

1. Review shows the safe derivative, its private status, supported type and
   bounded size, and a required `What do you want to remember?` field.
2. The note is plain owner-authored text, not an AI caption or extracted claim.
   It uses the existing 8,000 UTF-16-code-unit Capture bound and is never
   silently changed.
3. Before confirmation, no `dbo.captures` row exists. Closing preserves the
   uploaded private photo draft, but unsaved typed note text is not promised to
   persist in v1; the interface says so.
4. **Save private Capture** is the sole completion action. It requires a current
   source row-version, `needs_review`, a nonempty valid note, and explicit
   confirmation.
5. Replayed or concurrent saves return the same source/Capture link. They never
   create duplicate Captures.
6. Save does not create a Moment, placement, destination, share, audience,
   connection, tag, public page, or publication.

## Original and derivative truth

- The exact clean original remains privately attached as source evidence until
  explicit draft/Capture deletion.
- The original may contain device metadata such as location. PeerSlate does not
  parse or display those values in v1. The review warns that the private
  original is retained and that the safe preview strips embedded metadata.
- Product preview and any future projection must use the derivative, never the
  original, unless a later approved package defines a different explicit use.
- The member may explicitly download their own clean original. The response is
  owner-authorized, `private, no-store`, `nosniff`, and uses a generic filename.

## Existing Capture lifecycle

- Correction changes only the Capture note through PS-CAPTURE-002; source bytes
  and derivative remain unchanged.
- Archive/restore changes Capture availability but retains the private source.
- JSON export becomes schema version 3 for a photo Capture and distinguishes
  original/current Capture text, source metadata, derivative metadata, scan
  status, and owner-authorized original download path. It embeds no Blob URL or
  binary data.
- Draft deletion removes both original and derivative if present, then clears
  source content fields and leaves a body-free tombstone.
- Capture deletion removes original and derivative, clears source metadata,
  deletes Capture/revision content under the existing contract, and updates any
  Moment source link to the existing body-free tombstone before reporting
  success.

## Retention and bounds

- Confirmed source: retained privately with its Capture until explicit Capture
  deletion. No silent expiry.
- Unconfirmed source: retained until explicit deletion in Photo v1. The product
  shows this truth and gives a clear delete action.
- Abuse/cost bound: at most 10 nonterminal unconfirmed photo drafts per owner.
  An owner must finish or delete one before uploading another.
- Unsafe source: unavailable immediately and removed through the security
  cleanup path; only a body-free rejection/audit tombstone remains after
  provider retention completes.
- A future retention-policy change requires owner-visible notice, a migration,
  and a separate approved package; it may not silently delete existing sources.

## Definition of done

Photo is not done at a successful upload. Done means the complete signed-in
lifecycle—supported and rejected input, scan, safe preview, note, explicit save,
correction, archive/restore, export/download, deletion/retry, two-owner denial,
responsive/accessibility evidence, production pipeline, and homepage parity—is
accepted and verified.
