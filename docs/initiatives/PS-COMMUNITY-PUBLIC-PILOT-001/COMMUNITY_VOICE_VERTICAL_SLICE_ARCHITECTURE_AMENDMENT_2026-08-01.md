# Community Voice transient vertical-slice architecture amendment

**Package:** `PS-COMMUNITY-PUBLIC-PILOT-001`  
**Path:** Protected  
**Authority:** Pete-locked `2026-08-01-pete-voice-first-lock` A-H states  
**Scope:** one real Voice flow in the approved primary-Feed top-level comment
composer; default-off, local review only

## Why this amendment is needed

`PRIMARY_FEED_ARCHITECTURE_AMENDMENT_2026-08-01.md` already supplies the
accepted component map and six correct Community-to-Voice responsibilities.
Do not recreate it. One implementer-facing seam remained unspecified: the
exact request-only transcription contract, browser-memory boundary, safe error
semantics, and first propagation stop. This amendment supplies only that seam.

This tranche proves one reusable vertical path before it is copied into the
original-post and full-conversation composers. It is not Community Voice
completion and cannot make the pilot usable or releasable.

## Reused service boundary and endpoint

Add `CommunityVoiceService` in `services/community_voice_service.py`. It must:

- reuse `validate_audio` and the released `MAX_VOICE_BYTES` (20 MiB),
  `MAX_VOICE_DURATION_SECONDS` (180 seconds), supported-container validation,
  and `VOICE_LOCALE` (`en-US`) from `services.voice_capture_service`;
- inject and call the existing
  `speech_transcription_service.transcribe(...)` synchronously under the
  already configured server managed identity;
- validate the normalized provider transcript as nonempty and bounded in
  UTF-16 code units by `POST_BODY_MAX` for `post` or
  `CONTRIBUTION_BODY_MAX` for `contribution`, without truncation; and
- return only the proposal text and applicable context/limit. Drop provider
  request IDs, duration details, digests, audio, and provider payloads.

Do **not** call `VoiceCaptureService.create_and_transcribe`,
`confirm_capture`, Blob storage, SQL, Capture, Journal, or Community command
services. Those paths persist a private Voice source; Community dictation in
this slice is deliberately request-only.

Add exactly one command:

`POST /api/v1/community/voice/transcriptions`

It accepts multipart fields `audio`, `duration_seconds`, and
`composer_context`, where context is exactly `post` or `contribution`. Reject
unknown form or file fields. Context selects a text limit only; it never grants
identity, ownership, audience, target-post access, or publication authority.
The route must reuse the Community flag, same-origin checks, `_owner_identity`,
private/no-store response headers, and owner allowlist. It accepts no browser
user/owner/role/audience/post/contribution identity claim.

Successful status is `200` with:

```json
{
  "success": true,
  "proposal": {
    "text": "reviewable transcript",
    "composer_context": "contribution",
    "max_utf16_code_units": 2000
  }
}
```

No idempotency key is used because this command creates no durable state.
Explicit Retry resends the retained in-memory browser Blob and may consume a
second provider request. Add a `20 per hour` route limit and a route-specific
multipart ceiling of `MAX_VOICE_BYTES + 64 KiB`; do not raise the global
request limit.

## Data lifecycle and safe outcomes

- Browser audio chunks and the completed Blob exist only in the active page's
  JavaScript memory. They never enter `localStorage`, `sessionStorage`,
  IndexedDB, Cache Storage, an attachment collection, or a public URL.
- The browser may retain the Blob after a retryable transcription failure.
  Cancel, Discard, successful Use transcript, successful typed Send, card
  removal, or `pagehide` must stop tracks, revoke references, and clear audio
  and proposal state.
- The existing viewer-namespaced `localStorage` keeps typed text. A transcript
  becomes ordinary local draft text only after explicit `Use transcript`.
- Server audio exists only in the active multipart request, the bounded bytes
  passed to Speech, and any request-scoped framework spool. The application
  creates no named file, SQL row, Blob, cache entry, audit payload, or cleanup
  job; request teardown closes the upload and application references are
  released on every outcome.
- Azure Speech receives the private recording under the already released
  managed-identity provider contract. Do not claim that no AI service receives
  Voice input. Log only a generic safe outcome—never audio, transcript,
  multipart fields, provider bodies/IDs, or member identity.

Safe HTTP outcomes are:

| Status | Code | Semantics |
| --- | --- | --- |
| `401` | `authentication_required` | no trusted signed-in identity |
| `403` | `action_unavailable` / `same_origin_required` | non-owner or request-boundary denial |
| `415` | `multipart_required` | wrong request media type |
| `413` | `recording_too_large` | bounded request/file limit; not retryable with the same Blob |
| `422` | `invalid_context`, `recording_required`, `invalid_duration`, `recording_too_long`, `unsupported_recording`, `transcript_empty`, or `transcript_too_long` | safe validation failure; no silent truncation |
| `429` | `voice_rate_limited` | bounded retry-later state |
| `503` | `transcription_unavailable` | normalized provider/auth/timeout/malformed failure; retryable |

Every JSON failure includes `success: false`, the safe `code`, a member-facing
`message`, and `retryable`. No response includes protected/provider detail.

## Browser state boundary for the first surface

Implement one reusable controller inside `community-v1.js`, but attach it only
to the approved primary-Feed top-level comment composers in this tranche. A
page-wide registry permits at most one active recorder/request; another mic
cannot silently cancel or replace active work.

The controller must implement the exact lock:

`A ready -> B permission -> C recording -> D processing -> E editable
transcript preview -> explicit Use transcript -> H ready to send -> existing
Send`

`B/F/G` retain typed text and offer the locked retry, cancel/discard, and typed
fallback paths. Permission is requested only after explicit mic activation.
Stop is explicit. State D may not block typing. Retry in G reuses only the
in-memory Blob. Use transcript inserts the reviewed proposal at the textarea's
current selection without replacing existing text; if the combined body would
exceed 2,000 UTF-16 code units, preserve both texts and require editing instead
of truncating. Discard never changes the textarea.

The existing comment Send remains the only contribution command and reads only
the textarea. Voice never invokes it, creates an idempotency key, inserts text,
or publishes automatically. An uninserted preview is visibly excluded from
Send. Focus returns to the mic after cancel/failure and to the textarea after
Use transcript. Status changes are announced; waveform motion obeys reduced
motion; typing and the existing text-only Send path remain usable when media,
permission, network, or Speech is unavailable.

## Exact implementation reservation and verification

This tranche may change only:

- `community_api.py`
- `services/community_voice_service.py` (new)
- `app.py` (the one route-limit entry only)
- `templates/community_feed.html`
- `templates/community_pilot_policy.html` (truthful Speech disclosure only)
- `static/js/community-v1.js`
- `static/css/community-v1.css`
- `tests/test_community_voice.py` (new) and focused additions to
  `tests/test_community_public_pilot.py`
- package-scoped Community Voice evidence/completion records

Focused proof must cover service validation and UTF-16 limits; no SQL/Blob/file
write; owner, signed-out, non-owner, cross-origin, flag-off, multipart, size,
rate, no-store, provider-error, and no-content-in-log negatives; deterministic
A-H transitions; single-recorder ownership; track/reference cleanup; retry;
reviewed insertion without overwrite or truncation; no automatic insertion or
Send; existing namespaced draft/idempotent comment behavior; and text fallback.
Rerun the released Speech adapter/validation tests and the focused Community
suite. Capture comparable desktop/mobile real-browser evidence for A-H,
permission denial, provider failure, keyboard/focus, screen-reader status,
44-pixel targets, dark theme, reduced motion, and 200% reflow.

## Hard stop and forbidden scope

Stop after the primary-Feed comment vertical slice is locally proved. Keep
`PEERSLATE_COMMUNITY_PUBLIC_PILOT_ENABLED` default-off and return the exact diff
and evidence for Protected review and Pete's real-state visual check before
propagating the controller.

Do not touch the original-post composer, full-conversation/reply composers,
public confirmation, Capture/Journal Voice persistence, SQL, migrations,
Blob/media lifecycle, public audio/video, attachments, audience, identity,
navigation, Break, schema, Azure configuration, Candidate, PR, merge,
deployment, or flag activation. Those later Community composers remain a
release blocker even if this tranche passes.

The current Feed footer's broad statement that Community content is not sent
to AI becomes misleading when optional Speech transcription is active. Narrow
it truthfully while preserving the controlling rule that published Community
content is not sent to a generative model or used for AI ranking. The pilot
policy's generative-model boundary remains valid and should add only the
request-only private Speech disclosure.
