# Community Voice browser behavioral proof — 2026-08-02

## Harness boundary

These checks used the real Community template, CSS, and JavaScript with a
runtime-only Flask harness outside the repository. The harness was visibly
labeled, substituted a synthetic in-memory `MediaRecorder`, and returned a
deterministic transcript or safe failure. It read no microphone, called no live
Speech provider, and persisted or published nothing.

## Observed state and lifecycle behavior

| Proof | Browser observation |
|---|---|
| Permission request | The accessibility tree exposed a `status` reading “Requesting microphone permission. You can keep typing.” and a 44-pixel Cancel action. |
| Permission cancel | Cancel removed the panel, left Send disabled, and returned focus to `Start Voice comment recording`. A later media-promise settlement did not reopen a failure panel. |
| Recording | The tree exposed `Recording Voice comment` as pressed, the recording status, elapsed time, Stop, and Cancel. Stop was a visible cobalt primary action. |
| Recording cleanup | Cancel changed the state to `ready`, changed `aria-pressed` to `false`, returned focus to the mic, and the instrumented synthetic track recorded exactly one `stop()` call. |
| Processing/review | Stop produced an editable proposal and the live-region status “Review the transcript. It will not be inserted or sent until you choose Use transcript.” Focus moved to the proposal. |
| Insert, do not send | Use transcript removed the panel, focused the comment textarea, inserted the reviewed proposal, and enabled the existing Send button. It did not invoke Send or publish. Existing typed text was preserved in the insertion check. |
| Provider failure | A deterministic 503 showed “Voice transcription is unavailable…” with Retry and Discard while typing remained available. |
| Permission denial | A deterministic `NotAllowedError` showed “Microphone permission was not granted…” with Try again and Not now. |
| Single recorder | A two-card runtime fixture showed states `[recording, ready]` and pressed values `[true, false]` after the second mic was invoked. The visible status was “Finish or discard the other Voice comment before starting another recording.” |

The browser accessibility snapshot identified every state message as a status,
identified the proposal as `Editable Voice transcript proposal`, and exposed
the review, retry, discard, permission, and recording actions by accessible
name.

## Reflow, targets, theme, and motion

- At a 720 × 800 CSS-pixel viewport (the layout-equivalent of a 1440-wide
  desktop at 200% zoom), the browser reported no horizontal document overflow.
  The review controls remained reachable and measured 44 pixels high.
- The same recording and review flow was checked in the dark theme. The dark
  secondary control was corrected to use a dark surface with light-blue text
  rather than low-contrast blue text on white.
- The 390 × 844 narrow check kept the proposal, Use transcript, Discard, and
  the existing Replies & Updates shelf reachable without clipping or a second
  idle Voice panel.
- The focused stylesheet contract applies `animation-duration: .01ms`, one
  animation iteration, near-zero transitions, and automatic scrolling under
  `prefers-reduced-motion: reduce`. Voice has no functional dependency on the
  waveform or spinner animation; its state text and controls remain present.

## Evidence index

- `community-voice-recording-1440x1600-light.png`
- `community-voice-review-1440x1600-light.png`
- `community-voice-recording-1440x1600-dark.png`
- `community-voice-review-1440x1600-dark.png`
- `community-voice-review-390x844-light.png`
- `community-voice-review-controls-390x844-light.png`
- `community-voice-review-reflow-equivalent-720x800-dark.png`
- `community-voice-ready-to-send-reflow-equivalent-720x800-dark.png`
- `community-voice-permission-request-1280x720-light.png`
- `community-voice-permission-denied-1280x720-light.png`
- `community-voice-permission-cancel-cleanup-720x800-light.png`
- `community-voice-transcription-failure-1280x720-light.png`
- `community-voice-single-recorder-ownership-720x800-light.png`
- `community-voice-recording-cancel-cleanup-1280x720-light.png`

The screenshot filenames retain the requested viewport labels. The in-app
browser encodes captured bytes as JPEG even when the screenshot API is asked
for PNG; this affects encoding only, not the recorded viewport or UI state.
