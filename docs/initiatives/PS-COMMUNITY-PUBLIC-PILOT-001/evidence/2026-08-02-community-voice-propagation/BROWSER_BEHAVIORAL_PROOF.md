# Community Voice propagation browser proof

**Implementation commit:** `6ceb0d3b583dbb398cffb057eefed69ed84a5edb`  
**Self-review correction:** `619aacb`
**Route:** `http://127.0.0.1:5065/the-slate`  
**Harness:** `/tmp/peerslate_community_voice_preview.py` (runtime-only and not
committed)

## Truth boundary

The real Community template, CSS, and JavaScript ran in the in-app browser.
The local harness supplied Pete-only fixture content, an in-memory synthetic
`MediaRecorder`, and deterministic transcription success/failure responses.
It accessed no microphone, live Azure Speech, SQL, Blob storage, production
identity, or member content. The page visibly identified itself as a local
fixture. Browser screenshots were returned as JPEG bytes and therefore use
`.jpg` extensions.

## Observed behavior

- The top Feed microphone opened the existing private original-post composer
  and its one Voice controller. Permission, recording, explicit Stop,
  processing, editable transcript review, explicit Use transcript, and ready
  typed-draft states were observed.
- The original-post request used the post surface, accepted the reviewed
  proposal into the textarea only after Use transcript, and left `Review public
  post` as a separate action. An unresolved Voice review blocked the public
  confirmation and focused the Voice trigger. After Use transcript, `Review
  public post` opened the existing `Publish this post publicly?` confirmation;
  no publish action was selected.
- The full-conversation composer exposed one active Voice reply control.
  Recording, explicit Stop, editable review, Use transcript, and ready-to-send
  states were observed. The proposal remained visibly separate from the reply
  textarea until Use transcript, and the reply Send remained separate.
- Switching from the top-level conversation target to an exact contribution
  discarded the unresolved recording state, restored the target-specific text
  draft, returned to a ready microphone, and did not carry the proposal into
  the new reply target.
- A denied synthetic permission request showed the typed fallback with `Try
  again` and `Not now`. A deterministic transcription failure showed `Retry`
  and `Discard`; neither state changed typed text or sent content.
- The same page-wide controller registry remained the sole recorder/request
  owner across Feed, post, and reply instances. The existing primary-comment
  registry and track-cleanup proof remains recorded in the preceding protected
  slice; this propagation added no second registry or capture path.
- Status changes appeared as polite status regions. Focus moved to the editable
  proposal for review, returned to the textarea after Use transcript, and
  returned to the relevant microphone after blocked confirmation or failure.
- At a 390 by 844 viewport, original-post and reply review states produced no
  horizontal overflow (`documentElement.scrollWidth == innerWidth == 390`).
  Use transcript and Discard measured 44 CSS pixels high. Desktop light/dark
  and mobile dark states remained usable without clipped review controls.
- Browser console inspection found no error or warning entries in the success,
  permission-denied, or provider-failure tabs.

The browser runtime did not emulate an actual screen reader or operating-system
microphone prompt. Reduced-motion behavior remains the reviewed stylesheet
contract: Voice animation and transition durations collapse under
`prefers-reduced-motion`, while state and controls do not depend on animation.
The subsequent self-review correction keeps the same captured controller and
presentation while exposing it in edit mode and sharing the unresolved-Voice
pre-submit guard with `Save changes`; that narrow edit correction is covered by
focused contract tests and source review, not a separate browser capture.

## Captures

- `community-voice-post-review-1440x1000-dark.jpg`
- `community-voice-post-review-1440x1000-light.jpg`
- `community-voice-post-review-390x844-dark.jpg`
- `community-voice-reply-review-1440x1000-dark.jpg`
- `community-voice-reply-review-390x844-dark.jpg`
- `community-voice-post-permission-denied-1280x720-light.jpg`
- `community-voice-reply-provider-failure-1280x720-light.jpg`

The persistent success preview remains available at port 5065. Temporary
negative-state servers were stopped after capture, and the browser viewport
override was reset.
