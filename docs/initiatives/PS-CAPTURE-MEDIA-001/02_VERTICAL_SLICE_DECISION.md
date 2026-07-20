# PS-CAPTURE-MEDIA-001 - Vertical-Slice Decision

## Selected order

1. **Photo Capture** - first
2. **Document Capture** - second, after the shared source/scan lifecycle is live
3. **Video Capture** - third, after an explicit asynchronous media-processing
   architecture is approved

## Slice comparison

| Slice | First useful member outcome | Required new capability | Why it is or is not first |
| --- | --- | --- | --- |
| Photo | Take or choose one photo, review a safe preview, add the words that make it meaningful, and save one private photo Capture. | Malware scanning, strict image decoding, EXIF-safe derivative, dimensions, private preview/export/delete. | First. It proves the whole private-media contract without OCR, AI, extraction, streaming, or transcoding. |
| Document | Upload one PDF/DOCX/TXT source, scan it, review metadata and optionally extracted text, then explicitly save a private document Capture. | Active-content policy, password/encryption handling, secure rendering, extraction/OCR provider, long-text chunking, document accessibility. | Second. High owner value, but unsafe rendering and extraction create materially more security/provider work. |
| Video | Record or choose one short clip, scan/process it, review an accessible player and note, then save a private video Capture. | Large multipart uploads, verified duration/codecs, background queue, transcoding, thumbnails, streaming/range requests, captions, higher storage/egress cost. | Third. It should reuse the media source/scan model only after a real asynchronous processing foundation exists. |

## Photo first-slice boundary

The first released slice includes exactly one photo per source and:

- signed-in **Take photo** and **Choose photo** entry;
- JPEG and PNG only;
- maximum 10 MiB original payload;
- maximum 20 megapixels and maximum 8,192 pixels on either edge after trusted
  decode;
- private opaque original Blob;
- Defender for Storage on-upload scan with fail-closed status;
- server-decoded, orientation-corrected, metadata-stripped display derivative
  no larger than 2,400 pixels on its longest edge;
- required owner-authored `What do you want to remember?` text, up to the
  existing 8,000 UTF-16-code-unit Capture limit;
- explicit **Save private Capture** creating one `capture_type = photo` Capture
  and one stable source link;
- authorized preview/original download, versioned JSON export, archive/restore,
  correction, draft deletion, and Capture deletion; and
- all required idle, upload, scan, processing, review, error, stale,
  unavailable, deletion, keyboard, mobile, zoom, and reduced-motion states.

The limit and type checks are enforced independently in the browser and on the
server. The browser checks are guidance, not authorization.

## Explicit exclusions from Photo v1

- HEIC/HEIF, GIF, SVG, WebP input, RAW camera formats, multi-image Capture,
  albums, cropping, filters, annotations, and editing the original pixels;
- OCR, face/object recognition, geolocation extraction, automatic tags, AI
  captioning, AI proposals, or content moderation claims;
- public Blob/SAS URLs, direct-to-Blob browser credentials, CDN delivery, or
  client-provided storage paths;
- Moments, placements, downstream connections, shares, audience changes,
  publication, résumé/Story/Board/Interview/Feed/Journal writes; and
- migration or consolidation of existing Voice rows or blobs.

HEIC and other types are shown as unsupported with a clear path back to Type,
Voice, or a supported photo. No browser or server silently converts an
unsupported original.

## Later slice boundaries

### Document Capture

The document package starts from a new current-baseline audit. Its intended
first boundary is one scanned PDF, DOCX, or UTF-8 text file; private original;
safe metadata; provider-isolated extraction into an editable proposal; explicit
private save; authorized export; and deletion. It must resolve password-
protected files, macros/embedded objects, PDF active content, secure preview,
malware-scan failures, extraction provenance, long text, and OCR before entry.

### Video Capture

The video package starts only after a queue/worker/provider decision. Its
intended first boundary is one short MP4/WebM clip with bounded bytes and
duration; private original; scan; verified codec/duration; generated thumbnail;
transcoded playback derivative; captions or an equivalent accessible record;
explicit private save; authorized range delivery/export; and deletion. It may
not perform CPU-heavy transcoding inside a normal Flask request worker.

## Product rationale

Photo creates the clearest incremental step from the accepted `Attach photo`
promise. It lets a member preserve evidence of a real moment while keeping the
member's words authoritative. It also forces PeerSlate to solve the shared hard
parts—private binary source, quarantine, provenance, data rights, safe preview,
and distributed deletion—before higher-cost formats arrive.
