# Community Voice Primary Comment Checkpoint — 2026-08-02

## Outcome

The first protected Community Voice vertical slice is implemented for the
primary Feed card's top-level comment composer and is ready for independent
technical review. This is a local implementation checkpoint, not feature
completion, release readiness, Candidate activation, or deployment.

Implementation base: `5bf0af6f982034133dd4c2e455d027bf7c181f5b`

Authoritative `origin/main` fetched before final integration:
`d53686abfd68fb1b688b4a56a9976230ab77bea5`

Checkpoint commit: the commit containing this record

## Implemented boundary

- The existing compact microphone beside the primary comment Send button is
  the only newly active Voice affordance.
- Browser audio remains an in-memory `Blob`. It is sent only after explicit
  recording and Stop actions to a request-only Speech transcription endpoint.
- The endpoint derives and authorizes the owner identity server-side, requires
  same-origin multipart requests, accepts one bounded audio part, enforces a
  three-minute/20 MiB ceiling, independently checks the provider-measured
  duration, and is limited to 20 requests per hour.
- The Speech response returns an editable transcript proposal only. Provider
  identifiers and provider failure detail do not cross the boundary.
- The member must choose **Use transcript** before text enters the private
  local comment draft, then use the existing separate Send action to publish.
- Cancel, discard, send, Feed rerender, and page exit release audio, stream,
  request, and recorder references. No audio persistence was introduced.
- Permission, recording, processing, review, ready-to-send, unsupported,
  permission-denied, provider-failure, retry, discard, and three-minute-stop
  behavior are represented without blocking continued typing.

## Browser evidence

All browser evidence uses a clearly labeled runtime-only fixture with a
synthetic in-memory `MediaRecorder`. It reads no real microphone, calls no live
Speech provider, persists no content, and is not part of the repository diff.

- `evidence/2026-08-02-community-voice-primary-comment/community-voice-recording-1440x1600-light.png`
- `evidence/2026-08-02-community-voice-primary-comment/community-voice-review-1440x1600-light.png`
- `evidence/2026-08-02-community-voice-primary-comment/community-voice-recording-1440x1600-dark.png`
- `evidence/2026-08-02-community-voice-primary-comment/community-voice-review-1440x1600-dark.png`
- `evidence/2026-08-02-community-voice-primary-comment/community-voice-review-390x844-light.png`
- `evidence/2026-08-02-community-voice-primary-comment/community-voice-review-controls-390x844-light.png`
- `evidence/2026-08-02-community-voice-primary-comment/community-voice-review-reflow-equivalent-720x800-dark.png`
- `evidence/2026-08-02-community-voice-primary-comment/community-voice-ready-to-send-reflow-equivalent-720x800-dark.png`
- `evidence/2026-08-02-community-voice-primary-comment/community-voice-transcription-failure-1280x720-light.png`
- `evidence/2026-08-02-community-voice-primary-comment/community-voice-permission-request-1280x720-light.png`
- `evidence/2026-08-02-community-voice-primary-comment/community-voice-permission-denied-1280x720-light.png`
- `evidence/2026-08-02-community-voice-primary-comment/community-voice-permission-cancel-cleanup-720x800-light.png`
- `evidence/2026-08-02-community-voice-primary-comment/community-voice-single-recorder-ownership-720x800-light.png`
- `evidence/2026-08-02-community-voice-primary-comment/community-voice-recording-cancel-cleanup-1280x720-light.png`
- `evidence/2026-08-02-community-voice-primary-comment/BROWSER_BEHAVIORAL_PROOF.md`

The browser run verified explicit Stop, editable review, insertion after
existing typed text, separate enabled Send, narrow-layout access to both review
actions, safe retry/discard on provider failure, and Try again/Not now after
microphone denial.

## Protected review corrections

The first independent review of commit
`3d78794d94d10b647580d5eb367d5e20139e2ecb` did not pass. Its three findings
were addressed before the follow-up review:

- provider-measured duration now rejects recordings above three minutes even
  when an untrusted client reports a shorter duration;
- service-detected files over 20 MiB now return `413 recording_too_large`;
- behavioral evidence now covers single-recorder ownership, cancellation and
  track cleanup, focus and status semantics, dark theme, 44-pixel controls,
  narrow layout, and 200%-equivalent reflow without horizontal overflow.

## Verification

- 186 focused Community, Community Voice, XLSX, attachment, and adjacent Voice
  service/UI tests passed.
- 214 adjacent Community-tab, navigation, Community/Journal-boundary, and
  Workshop tests passed; one expected test was skipped.
- 10 Community focus-lifecycle behavioral checks passed.
- JavaScript syntax, Python compilation, dependency integrity, and diff
  whitespace checks passed.

## Deliberately not begun

- Voice activation in the original-post composer
- Voice activation in full-conversation or nested-reply composers
- Audio publication as a Feed attachment
- Azure Blob persistence or retention work
- SQL or schema migration work
- live Azure Speech browser evidence
- Candidate activation or feature-flag enablement
- PR, push, merge, deployment, or public/live claims

## Next gate

Run an independent protected technical review of the exact local checkpoint
commit. Resolve any findings and stop. Pete must explicitly authorize
propagation of the approved Voice behavior to the remaining composers or any
release tranche.
