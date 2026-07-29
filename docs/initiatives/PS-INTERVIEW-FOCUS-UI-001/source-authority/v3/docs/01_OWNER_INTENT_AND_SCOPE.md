# 01 — Owner Intent and Scope

## Core intent

Interview Studio already has valuable functionality. The UI must reveal the active task rather than surrounding it with equal-weight content.

> **Do not remove capability. Give each capability the right moment.**

## Shared UX requirements

### Active-task dominance

The mode-specific task dominates the active viewport:

- Interview Me: question + textarea + Review My Answer.
- Interview AI: question + answer-basis choice + generated answer workspace.
- Video Practice: question + camera stage + recording control.
- History: local records and meaningful next action.

Marketing/orientation content, inactive future states, long explanations, advanced settings, and secondary evidence must not compete with the task.

### Type-first text entry

Where text is entered:

1. The real input is visible and immediately usable.
2. Typing is the default path.
3. Dictation is a secondary utility labeled `Dictate` or repository-approved equivalent.
4. Loading a route may not request microphone permission.
5. Dictated text enters the same input and remains editable.
6. Denial, timeout, or unavailability never blocks typing or submission.

### Progressive disclosure

Only the active state is exposed. Loading, generated results, feedback, comparison, transcript coaching, playback actions, errors, and recovery tools appear when relevant. Inactive future states must not remain visually present or exposed to assistive technology.

### One dominant action

Each state has one visually dominant next action. Secondary and destructive actions remain available but clearly subordinate.

### Existing-site continuity

Reuse the real PeerSlate shell, navigation, typography, icons, theme mechanism, route semantics, data behavior, and truth language. Mockups control hierarchy and relationships, not fabricated functionality.

## Product-area scope

### Interview Me — complete state implementation

Ready, typed draft, optional dictation, queue, processing, review, improve, retry/continue, failure recovery, desktop/tablet/mobile, light/dark.

### Interview AI — complete state implementation

Preserve and redesign the complete released behavior:

- best-practice example;
- approved public-history answer;
- side-by-side compare;
- custom question entry;
- optional dictation into the same question input;
- explicit generation;
- answer, reasoning, source/history evidence, and comparison labeling;
- follow-up generation;
- Practice This Answer transfer;
- New Question;
- loading, empty, no-grounding, and failure recovery states.

Interview AI must remain an evidence-labeled answer lab, not become a generic chat screen.

### Video Practice — complete state implementation

Preserve and redesign the complete local-only behavior:

- explicit camera enable;
- device permission/request/denial/unavailable states;
- camera preview;
- local recording timer;
- stop, playback, retake, discard, and new-question behavior;
- device settings;
- local-only truth;
- transcript coaching through a separately typed, pasted, or optionally dictated text input;
- no unsupported pace, eye-contact, filler-word, clarity, or confidence analytics;
- no media upload or persistent recording claim.

### History — shared shell and honest hierarchy

Browser-local records, goals, detail, deletion, and storage-unavailable states remain honest. Do not imply account-backed history, cross-device synchronization, or retained video media.
