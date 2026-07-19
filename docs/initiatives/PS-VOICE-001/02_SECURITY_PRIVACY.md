# PS-VOICE-001 Security and Privacy Contract

## Trust boundaries

- Browser input is untrusted, including MIME type, duration, file name, source key, row version, and transcript edits.
- Owner identity comes only from the existing authenticated server session/header contract.
- SQL procedures independently resolve ownership for every read and write.
- Blob and Speech access happens only on the server under the App Service managed identity.

## Private media rules

- Blob public access is disabled at account and container level.
- Blob names are random opaque identifiers under a fixed server-owned prefix. They contain no owner key, email, profile slug, transcript, original file name, or Capture body.
- Do not put transcript text or identity into Blob tags/metadata.
- Playback/download is proxied or streamed through an authenticated owner route with `Cache-Control: private, no-store`, `X-Content-Type-Options: nosniff`, a safe disposition, and a server-selected content type.
- Never issue a public or reusable SAS URL to the browser in this slice.

## Validation

- Enforce 20 MB at the web server before any provider call. Reject chunked or ambiguous over-limit bodies safely.
- Accept only an explicit allowlist of browser-recordable formats that the selected Speech endpoint officially supports. Validate magic/container characteristics where practical; MIME alone is insufficient.
- Enforce the 3-minute client limit and verify server-side duration when the selected format permits reliable inspection. Reject malformed, zero-byte, and implausible media.
- Normalize reviewed transcript text under the existing 8,000-character Capture limit. Do not silently truncate.
- Treat provider responses as untrusted and validate shape, locale, and size before persistence.

## Authorization negatives

Tests must prove a second owner cannot discover existence, state, transcript, Blob, Capture link, export, error details, or deletion status through guessed keys, stale tokens, downloads, retries, or timing-sensitive write paths.

## Secrets and configuration

- Use `DefaultAzureCredential`/managed identity in production.
- Do not use, request, print, commit, or expose storage keys, connection strings, Speech keys, bearer tokens, or credentials.
- Nonsecret app settings may name the Blob account URL/container, Speech endpoint/API version, locale, maximum bytes, and maximum duration.
- Logs and audits may include opaque entity keys, safe state codes, byte counts, duration, locale, provider operation IDs, and outcomes. They may not include audio bytes, transcript text, member content, provider response bodies, tokens, or storage paths that reveal identity.

## Data rights

- Archive retains private audio and transcripts.
- Export clearly distinguishes original media metadata, provider transcript provenance, approved Capture body, and correction history. Audio bytes are delivered only through an owner-authorized export response.
- Delete removes audio bytes, raw transcripts, approved text, and correction text. A body-free tombstone may preserve event type, opaque entity key, timestamps, actor, outcome, and safe reason code.
- A failed deletion remains visible to the owner as incomplete and retryable; it is never presented as complete.
