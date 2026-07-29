# 15 — Video Practice Complete Implementation Contract

## Purpose

Video Practice is a local camera-rehearsal environment. It helps the user record, play back, and repeat an answer on their own device. It may also let the user separately type, paste, or optionally dictate a transcript for the same content coaching used elsewhere.

It is not currently an automated delivery-analysis product unless the repository proves a real released analysis service. The redesign must make the local rehearsal feel premium without implying upload, retention, pace analysis, eye-contact analysis, filler-word analysis, confidence scoring, or employer prediction.

## Authority

- `references/authoritative_mockups/07_video_practice_light.png` controls desktop geometry, preview dominance, question placement, control hierarchy, device rail, and local-only visual truth.
- This document controls all additional media states not pictured in Screen 07.
- Existing repository behavior controls browser APIs, recorder lifecycle, device selection, local blob/object URL handling, transcript coaching, history metadata, and cleanup.

Any discovered media upload, retention, or analysis behavior that contradicts the released truth language is a stop condition for owner review before UI implementation continues.

## Required desktop composition

### Shared shell

Use the same Interview Studio header, mode selector, session summary, white foundation, and contextual-rail structure as the other modes.

### Question banner

- Current question remains immediately above the camera stage.
- Include progress and essential metadata.
- Do not let the header/marketing content push the camera below the first viewport.

### Local video stage

- Dominant 16:9 or current repository-approved preview area.
- Local-only badge attached to the stage.
- Elapsed timer attached to the stage while recording/playback metadata is relevant.
- Primary controls centered or placed in a stable stage footer.
- Native/existing video controls preserved where appropriate.

### Context rail

- Device status and settings.
- Current recording state and elapsed duration.
- Honest after-stop choices.
- No empty analytics dashboard.

### Transcript coaching

- Secondary to active camera rehearsal.
- Hidden/collapsed while actively recording unless the released UI requires simultaneous access.
- Available before or after recording as current behavior allows.
- Clearly separate text coaching from the local video media.

## Permission and device states

### Camera off

- No media permission requested on route load.
- Show the current question and a calm camera-off stage.
- One primary `Enable Camera` action.
- Concise truth: nothing is uploaded.

### Permission requesting

- Keep question and stage geometry stable.
- Explain that the browser is requesting camera/microphone access.
- Avoid indefinite spinner; preserve current timeout/recovery behavior.

### Permission denied

- Clearly identify denied camera and/or microphone.
- Provide current recovery instructions/device settings action.
- Do not repeatedly re-prompt without user action.
- Transcript coaching remains usable through typing/paste even if media is unavailable.

### Device unavailable/error

- Distinguish no device, busy device, unsupported browser/API, and generic failure only to the extent the current implementation can truthfully do so.
- Preserve retry/device-settings behavior.
- Do not show a fake black preview as if connected.

### Preview ready

- Show live local preview.
- `Start Answer` is the sole primary action.
- Device settings and New Question remain secondary.
- Local-only status remains visible but not alarmist.

## Recording states

### Recording

- `Stop Recording` is the sole primary action.
- Elapsed timer is clear.
- Discard is secondary/destructive and may require existing confirmation.
- Do not expose transcript submission, analytics, or unrelated controls as equal-weight actions.
- Prevent accidental double-start/double-stop through existing state handling.

### Stopping/finalizing local blob

- Keep preview/stage stable.
- Show a brief in-place finalizing state only if real processing exists locally.
- Do not imply server processing.

### Playback ready

- Show local playback in the same dominant stage.
- Make the next most valuable existing action primary, normally `Add/Review Transcript for Coaching` or repository-approved equivalent if that path exists.
- Keep `Record another take`, `Discard`, and `New Question` available and subordinate according to current behavior.
- State that playback is local and may disappear when the user leaves/discards if that is true.

### Retake

- Use existing cleanup/reset behavior.
- Do not retain multiple takes unless the current product already does.
- Preserve question/session context.

### Discard

- Explicit destructive action.
- Revoke/release the current local object URL/blob according to existing lifecycle.
- Do not delete unrelated History records or transcript drafts.

### Route exit and cleanup

Codex must verify and preserve:

- stopping all live MediaStream tracks;
- stopping/canceling MediaRecorder safely;
- clearing timers/listeners;
- revoking object URLs when no longer needed;
- preventing camera/microphone activity after leaving the mode;
- retaining only the data the current implementation intentionally retains.

## Transcript coaching contract

### Truth

Automatic transcription is not implied unless a real released service exists. The UI must say the user can type, paste, or optionally dictate what they said.

### Input

- Real transcript textarea is the source of truth.
- Typing and paste are primary.
- Optional dictation writes into the same textarea.
- Camera permission is not required to use transcript coaching.
- Recording media is not attached to the coaching request unless the repository proves otherwise.

### Submission

- `Submit Transcript` remains explicit.
- Reuse the current content-coaching request, payload, response, error, review, and improvement behavior.
- Preserve the transcript on failure.
- Keep local playback available during coaching only if the released lifecycle safely supports it.

### Result

- Content feedback is labeled as transcript/content coaching, not delivery analysis.
- Do not infer pace, pauses, eye contact, filler words, confidence, or vocal clarity from typed text.

## History truth

- Save only the current released browser-local metadata/record.
- Do not claim the recording itself is retained if it is not.
- Clearing browser data or leaving/discarding may remove playback; explain truthfully.
- No account, cloud, or cross-device claim.

## Mobile and orientation behavior

- Camera preview is full width within safe margins.
- Recording controls remain reachable above browser and OS safe areas.
- Portrait is the default design authority; landscape 844×390 must remain functional.
- Device settings open as a sheet/drawer.
- Question may collapse to a sticky summary while preserving access.
- On-screen keyboard for transcript coaching must not cover the textarea or Submit Transcript.
- Orientation change must not silently lose the stream, recording, or transcript beyond browser limitations already handled by the product.

## Accessibility

- Every media action has an explicit text label and state.
- Device/recording changes are announced without flooding live regions.
- Focus returns logically after permission errors, stopping, discard confirmation, or sheet closure.
- Do not rely on red/green alone for recording/device state.
- Timer is not announced every second; provide a non-noisy accessible status.
- Keyboard users can operate enable, start, stop, playback, retake, discard, device settings, transcript, and submission.

## Network and privacy proof

Required implementation evidence:

1. Capture network traffic during enable, preview, recording, stopping, playback, retake, discard, and route exit.
2. Prove no audio/video body, blob, multipart media, object URL, or encoded media is transmitted.
3. Separately prove transcript coaching sends only the current text/question data expected by the released endpoint.
4. Inspect storage to prove no new persistent video storage key or retained blob was introduced.

## Prohibited redesigns

- Remote interviewer avatar or simulated video call.
- Automatic recording on page load.
- Permission request on page load.
- Media upload or cloud retention.
- Fake pace, filler, eye-contact, clarity, confidence, or delivery scoring.
- Treating transcript coaching as automatic analysis of the video.
- Empty analytics cards labeled “coming soon” inside the active task.
- New media libraries or dependencies unless repository-grounded necessity is approved.

## Video Practice acceptance checklist

- [ ] No permission prompt before explicit user action.
- [ ] Camera-off, requesting, denied, unavailable, ready, recording, stopping, playback, retake, discard, and cleanup states are implemented.
- [ ] Preview/record/playback remain local.
- [ ] No network media upload occurs.
- [ ] Transcript coaching works without a recording.
- [ ] Typing/paste is primary; dictation is optional.
- [ ] Content feedback is not mislabeled as delivery analysis.
- [ ] No unsupported analytics appear.
- [ ] Mobile portrait/landscape controls remain reachable.
- [ ] Tracks, recorder, timers, and object URLs are cleaned up correctly.
