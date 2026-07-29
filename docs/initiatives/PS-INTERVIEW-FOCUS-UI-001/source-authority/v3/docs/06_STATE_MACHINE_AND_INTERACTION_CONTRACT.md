# 06 — State Machine and Interaction Contract

## Interview Me canonical states

- ready-empty
- drafting-typed
- dictation-requesting
- dictation-listening
- dictation-stopped
- dictation-denied/unavailable
- queue-open
- submitting
- coaching-processing
- coaching-success
- coaching-failure
- improve-processing
- improve-ready
- retrying
- advancing

Type-first path:

`ready-empty → drafting-typed → submitting → coaching-processing → coaching-success → improve-ready or retrying or advancing`

The full path works without microphone use.

## Interview AI canonical states

- ai-empty
- ai-question-drafting
- ai-dictation-requesting/listening/denied
- ai-generating
- ai-answer-ready-best-practice
- ai-answer-ready-public-history
- ai-answer-ready-compare
- ai-no-grounding
- ai-generation-failure
- ai-follow-up-drafting
- ai-follow-up-generating
- ai-follow-up-ready
- ai-follow-up-failure
- ai-practice-transfer-confirmation-if-current
- ai-practice-transfer-complete

Canonical path:

`ai-empty → ai-question-drafting → ai-generating → one answer-ready state → follow-up or practice transfer or new question`

Changing answer basis uses existing behavior. It may regenerate only if the released implementation currently requires generation; it may not silently rewrite a displayed result without an explicit existing trigger.

## Video Practice canonical states

- video-camera-off
- video-permission-requesting
- video-permission-denied
- video-device-unavailable
- video-preview-ready
- video-recording
- video-stopping
- video-playback-ready
- video-discard-confirmation-if-current
- video-retake
- video-transcript-drafting
- video-transcript-dictation-optional
- video-transcript-submitting
- video-transcript-coaching-success
- video-transcript-coaching-failure
- video-route-exit-cleanup

Canonical local recording path:

`video-camera-off → video-permission-requesting → video-preview-ready → video-recording → video-playback-ready → retake or discard or new question`

Optional content-coaching branch:

`video-transcript-drafting → video-transcript-submitting → existing coaching success/failure flow`

The recording itself is not sent with the transcript unless the current repository proves otherwise; any such contradiction is a stop condition for owner review.

## Cross-mode invariants

- Current text input value remains the source of truth until explicit submission/generation.
- Opening settings, queue, answer-basis selection, source details, device settings, drawers, or theme does not silently lose work.
- Loading a mode does not request microphone or camera permission.
- No generated answer or coaching result appears until a complete real response exists.
- Failure preserves the relevant question, draft, answer, basis, recording/playback availability, or transcript.
- Destructive actions remain explicit.
- Theme switching preserves state.
- Mode switching follows released route/state behavior and existing confirmation rules.
- No hidden audio/video upload or fabricated analysis.
