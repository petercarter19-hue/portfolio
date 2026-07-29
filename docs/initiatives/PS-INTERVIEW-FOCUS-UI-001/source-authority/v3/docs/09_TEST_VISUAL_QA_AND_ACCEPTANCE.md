# 09 — Test, Visual QA, and Acceptance

## Required functional regression

### Interview Me

- Type-only complete session: draft, autosave, submit, processing, review, improve/retry/next/history.
- Optional dictation: granted/denied/unavailable/timeout; recognized text enters same textarea; typing remains available.
- Settings/queue/example/theme opened during a draft without loss.
- Coaching success/failure with answer preservation.
- Improve draft explicit application and original preservation.

### Interview AI

- Each released answer basis produces the expected request mapping and labeled result.
- Typing works without dictation.
- Optional dictation writes into the same question input.
- Loading, success, no-grounding, server/network failure, and retry preserve the question and selected basis.
- Why-it-works/reasoning, evidence/history, comparison, and source labels map only to real data.
- Follow-up remains locked/unlocked according to existing behavior and keeps the same grounding.
- Practice This Answer uses existing transfer behavior and does not silently overwrite a nonempty draft.
- New Question resets only the state currently reset by the released implementation.

### Video Practice

- Route load makes no camera/microphone permission request.
- Enable Camera, permission granted/denied/unavailable, device settings, preview, recording, stop, playback, retake, discard, new question, and route-exit cleanup.
- Recording remains local; network inspection shows no media upload.
- Playback availability and duration are honest.
- Transcript can be typed/pasted without media; optional dictation remains secondary.
- Submit Transcript uses only the current text coaching request and preserves failure recovery.
- No unsupported pace, eye-contact, filler-word, clarity, confidence, or delivery analysis is rendered or announced.
- History retains only the currently released local metadata; no retained-video claim.

### History and shared shell

- Browser-local keys and storage-unavailable handling.
- Theme/mode/session switching without accidental state loss.
- Public-demo identity and approved-public-history boundaries.

## Exact visual authority captures

| Screen | Required viewport |
|---|---|
| 01–10 | 1440×900 authority comparison; also validate ready states at 1536×1024 and 1366×768 |
| 11–14 | 390×844 authority comparison |

Screens 06 and 07 are geometry authorities. Additional Interview AI and Video Practice states must be captured at 1440×900 and 390×844 using the same component geometry even though they do not add to the 14-screen authority count.

Additional evidence: 1024×768, 834×1194, 844×390, 320×568, 200% zoom, reduced motion, long question, long generated answer, long source list, permission failure, storage unavailable, and network failure.

## Acceptance gates

- Light canvas reads white, not warm beige/ivory/cream.
- In every mode, the active task is identifiable within five seconds.
- Interview Me and all transcript/question inputs are type-first.
- Dictation is optional, adjacent, and nonblocking.
- Interview AI is an evidence-labeled answer workspace, not generic chat.
- Interview AI source basis and provenance remain visible and truthful.
- Video preview/recording is dominant when active and explicitly local-only.
- No media upload or fabricated delivery analytics.
- One action is primary per state.
- Supporting material is present but quiet.
- Inactive future-state panels are not exposed.
- Mobile keyboard, camera controls, and sticky actions do not cover active content.
- Failure preserves the complete relevant state.
- No route/endpoint/payload/storage/auth/database/media/AI-contract change.
- Light/dark share the same DOM, actions, order, and responsive behavior.
- No unsupported account persistence, private-history access, publication, or employer prediction is implied.
