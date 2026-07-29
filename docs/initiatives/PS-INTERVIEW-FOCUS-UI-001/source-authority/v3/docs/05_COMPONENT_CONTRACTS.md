# 05 — Component Contracts

## Shared components

### InterviewStudioShell

Reuses the production global shell and exposes active mode, session summary, theme, profile/public-demo context, and route content. It may not own or duplicate business logic already owned elsewhere.

### ModeSelector

Contains Interview Me, Interview AI, and Video Practice. History is adjacent but visually separate. Active state is route-driven. Keyboard navigation and focus treatment follow existing patterns.

### SessionSummary

Shows real experience level, question family, and session format. Edit Session invokes existing configuration behavior without losing draft, generated answer, or recording state unless the released product already requires a confirmation.

### WorkspaceGrid

Provides the shared main-stage/context-rail relationship. It controls layout only and must not become a business-state owner.

### ContextRail / MobileDrawer

Provides supporting content without taking over the task. Opening/closing preserves draft, selected answer basis, generated content, recording state where safe, scroll, focus, and route state.

### Status announcements

Autosave, generation, dictation, processing, device, recording, success, and failure use appropriately scoped live regions without repeated or noisy announcements.

## Interview Me components

- `QuestionStage`
- `AnswerComposer`
- `DictationControl`
- `ProcessingPanel`
- `CoachingReview`
- `ImproveWorkspace`

The real textarea remains the single answer source of truth.

## Interview AI components

### AIQuestionComposer

- Uses the released question input as the source of truth.
- Typing is primary; optional dictation writes into the same input.
- `Get Answer` remains explicit and follows existing validation.
- Does not behave like a free-running chat composer.

### AnswerBasisSelector

- Radio-group semantics for Best-practice, Approved public history, and Compare.
- Selected basis remains visible while viewing the answer.
- Labels include concise truth language, not color-only distinction.
- Uses existing internal values and request mapping.

### AIAnswerWorkspace

- Maps only real response fields.
- Keeps source/basis label adjacent to the generated answer.
- Presents answer first, then why it works/reasoning, then evidence/history, then comparison/structural lessons as applicable.
- Empty, generating, success, no-grounding, and failure states share one geometry.

### SourceEvidencePanel

- Displays only approved source/history evidence actually returned or already available through released logic.
- Never fabricates citations or private-history access.
- May collapse on mobile but must remain discoverable and labeled.

### FollowUpComposer

- Appears only when the released unlock condition is met.
- Preserves grounding continuity and current request semantics.
- One explicit Ask action; no autonomous conversation loop.

### PracticeTransferAction

- Invokes the existing `Practice This Answer` behavior.
- Must not silently replace a nonempty Interview Me draft.
- Uses existing confirmation and state-transfer logic; no new persistence or publication.

## Video Practice components

### VideoQuestionBanner

Keeps the current question, progress, metadata, and approximate answer time visible without shrinking the preview excessively.

### MediaPermissionPanel

- Explicit `Enable Camera`/released equivalent.
- Shows requesting, denied, unavailable, and recoverable states.
- Loading the route does not request camera or microphone permission.

### LocalVideoStage

- Owns presentation of the existing local media stream/recorded blob only.
- Shows local-only status and elapsed time.
- Uses native or existing playback behavior.
- Does not upload, analyze, or imply retention.

### RecordingControls

- Ready: Start Answer is primary.
- Recording: Stop Recording is primary; discard is secondary/destructive.
- Playback: next-step action is primary; retake and discard remain available.
- Uses existing handlers and state; no duplicate media controller.

### DeviceStatusRail

Shows real camera/microphone/request/connection status and opens the existing device-settings behavior.

### TranscriptCoachingPanel

- Separate text input for what the user said.
- Typing/paste is primary; dictation optional if already supported.
- Does not claim automatic transcription.
- Submit Transcript invokes the current content-coaching path only.
- Media and text remain separate sources; no hidden upload.

### LocalRehearsalResult

Shows only real local metadata/status such as elapsed duration and playback availability. Explicitly states unavailable analytics rather than drawing empty scorecards.
