# 06 — State Machine and Interaction Contract

Codex must map these semantic states to the application's existing real state variables. Do not create duplicate product state.

## State model

| Semantic state | Visible main-stage content | Dominant action | Supporting UI |
|---|---|---|---|
| `ready-empty` | Full question, metadata, intent, empty composer | Review My Answer disabled | session, Up Next, nudge, privacy |
| `drafting` | Full/sticky question, editable composer with text | Review My Answer | saved/word status, voice, queue disclosure |
| `dictation-requesting` | Same composer; permission/request status | Cancel/continue according to current behavior | concise permission explanation |
| `dictation-listening` | Sticky question, live editable text, listening state | Review My Answer | Stop, waveform/status, Up Next |
| `dictation-stopped` | Editable text remains | Review My Answer | Speak again, save state |
| `dictation-denied` | Editable text remains fully usable | Review My Answer | truthful recovery/type-instead message |
| `queue-open` | Current question summary + composer | Review My Answer | queue occupies rail/drawer; draft remains |
| `submitting` | Preserved submitted answer | none/disabled | request begins once |
| `coaching-processing` | Submitted answer + in-place progress | none or cancel only if current product supports it | quiet session/privacy rail |
| `coaching-success` | Review content | Improve Answer | Try Again, Next Question, current state rail |
| `coaching-failure` | Submitted answer + error/recovery | Retry coaching | Keep editing; answer-safe truth |
| `improve-processing` | Original answer + honest pending improved-draft area | none/disabled | source/grounding truth |
| `improve-ready` | Original + editable improved draft + change summary | Use This Draft | Back to Feedback, Retry Out Loud |
| `retrying` | Same question returns to editable answer state | Review My Answer | attempt/history semantics preserved |
| `advancing` | next existing question | state-dependent | progress updates once |

## Transition contract

### Starting Interview Me

- Preserve current route/start semantics.
- If the base route retains an orientation view, `Start Interview Me` transitions to `ready-empty` without leaving a large hero above the workspace.
- Direct links to Interview Me open the focused ready state immediately.
- Do not add a new route solely for the new UI.

### Typing

- First input moves `ready-empty` to `drafting`.
- Autosave behavior and debounce remain unchanged.
- The submit action becomes available according to existing validation.
- No supporting panel reflow should move the textarea under the user's cursor.

### Starting dictation

- Existing permission and browser support checks run unchanged.
- Do not clear or replace existing text.
- Status is announced once.
- Dictated text appears at the current/defined insertion point according to existing behavior.
- The same textarea remains editable during and after listening unless the current implementation truthfully requires otherwise.

### Opening the queue

- Desktop: rail transitions to queue drawer/content without changing the main-stage width unexpectedly.
- Mobile/tablet: bottom sheet or drawer opens above the action dock.
- Background question/answer remain intact.
- If selecting another question would replace a nonempty draft, preserve the existing confirmation setting and modal.

### Submitting

- Validate using current rules.
- Freeze/capture the submitted snapshot according to current implementation.
- Send exactly the current existing payload to the current existing endpoint.
- Guard against duplicate submission.
- Preserve the visible answer and move to `coaching-processing` in the same stage.
- Do not scroll the user to an unrelated section or page.

### Processing

- Keep the answer visible.
- Focus remains stable; do not focus a spinner.
- Use one polite status region.
- If the response succeeds, replace the processing panel with review content.
- If it fails, replace the processing panel with failure recovery.

### Review success

- Move focus to the review heading only if it improves keyboard/screen-reader continuity and does not unexpectedly yank a pointer user's viewport. Prefer programmatic focus with `tabindex="-1"` after the state change.
- Do not expose empty Improve panels before the user chooses Improve Answer.
- Preserve automatic browser-local history behavior exactly.

### Improve Answer

- Call the existing improve behavior.
- Keep the original answer immutable/preserved.
- Render the returned improved draft as editable.
- Keep source/grounding truth.
- Applying/using the draft performs only the existing action. It must not imply saving to an account, publishing, or changing the public Slate.

### Retry

- Preserve the current question and attempt semantics.
- Do not overwrite the completed review/history record unless current behavior already does so.
- Make the selected answer editable in the existing way.

### Next Question

- Advance exactly once.
- Update question number/progress, queue, metadata, and composer state.
- Preserve completed attempt/history according to current behavior.

### Failure

- Submitted and draft text remain available.
- `Keep editing` returns to the current editable answer without reconstruction.
- `Retry coaching` reuses the same question and answer through the existing request path.
- Never show partial fields as if a complete review exists.

## Mode changes

Switching Interview Me / Interview AI / Video Practice must preserve all state the existing product currently preserves. Theme changes must not reset:

- draft text;
- selected question/mode;
- queue/settings dialog;
- history;
- media permission or current local recording state where technically possible;
- focus;
- scroll position.

Do not promise preservation that current browser media APIs cannot truthfully provide; preserve existing behavior and document any browser limitation.

## Progressive-disclosure contract

Before coaching success, do not visibly or programmatically expose:

- empty score cards;
- empty strengths/improvements;
- empty STAR map;
- empty improved draft;
- history analytics that depend on absent records.

Supporting content is revealed only by:

- current state;
- an explicit user disclosure action;
- real existing data.

## Focus contract

- Opening a dialog/drawer moves focus into it.
- Closing returns focus to the opener.
- State updates do not reset focus to `<body>`.
- Sticky/fixed controls may not cover the focused element.
- Theme changes retain focus.
- Error summary is announced and focusable without creating a trap.

## Live-region contract

Use separate, minimal announcements:

- save status: polite, throttled;
- dictation status: polite;
- coaching request status: polite;
- final error: assertive/`role="alert"` once;
- review completion: polite, then optional focus to heading.

Do not place rapidly changing timers, word counts, or waveforms in a verbose live region.
