# 05 — Component Contracts

These are conceptual component boundaries. Implement them using the repository's existing Flask/Jinja/HTML/CSS/JavaScript architecture. Do not migrate to React or force a framework abstraction that does not fit the codebase.

## General rules

- Prefer existing partials, macros, utility classes, icons, and tokens.
- Extract only where it reduces duplicated state markup or inconsistent behavior.
- Keep the textarea, selected question, request state, media object, and history state single-sourced.
- Do not render duplicate interactive controls for desktop and mobile unless both are synchronized and only one is focusable/accessible at a time.
- Use semantic HTML before ARIA.
- Inactive state panels must use `hidden`, conditional rendering, or equivalent; visual offscreen positioning alone is insufficient.

## Conceptual inventory

### 1. `StudioHeader`

**Inputs:** public-demo label, title, subtitle, identity display, theme state.  
**Behavior:** no independent product state; reuses global shell.  
**Accessibility:** one page-level `h1`; demo identity wording remains truthful.

### 2. `PracticeModeSwitcher`

**Inputs:** current mode, existing URLs, mode descriptions.  
**States:** default, hover, focus, active, unavailable only if current code supports it.  
**Contract:** links remain real links; do not replace navigation with non-semantic div clicks.  
**History:** rendered as separate destination, not within the three-mode group.

### 3. `SessionSummaryBar`

**Inputs:** experience, question family, session format/length.  
**Action:** opens existing settings.  
**Contract:** current values always reflect real session state.  
**Mobile:** one-line truncation may visually shorten labels, but full text remains accessible.

### 4. `QuestionStageHeader`

**Inputs:** question number, total, percentage, state label, question text, family, competency, framework, expected time, interviewer intent.  
**Variants:** full ready state; compact sticky state.  
**Contract:** only one accessible question heading. If a visual sticky clone is required, mark the duplicate appropriately and preserve a single programmatic label.

### 5. `AnswerComposer`

**Inputs/state:** current answer text, saved status, word count, dictation state, submit eligibility, validation.  
**Required child controls:** textarea, optional dictation control, stop state, save/word status, submit action, privacy line.  
**Contract:**

- textarea remains the canonical text value;
- dictation inserts into the same value;
- voice start/stop never clears typed text;
- submit uses existing validation and endpoint;
- disabled state has a discernible reason;
- status changes do not steal focus;
- keyboard shortcut remains.

### 6. `ContextRail`

**Inputs:** current mode and current state.  
**Variants:** ready, queue, processing, review, improve, AI basis, video device, history summary.  
**Contract:** rail content supports the current task; it does not render all variants simultaneously.  
**Responsive:** becomes an accordion, drawer, or bottom sheet below the desktop threshold.

### 7. `QuestionQueue`

**Inputs:** ordered queue, current question, competency labels, custom-question capability.  
**Contract:** selection invokes existing behavior and confirmation; no silent draft loss.  
**Accessibility:** labeled list; current item identified; close button; focus return.

### 8. `SubmittedAnswerCard`

**Inputs:** immutable submitted snapshot and optional current visibility controls.  
**Contract:** clearly labeled preserved/context; never substitutes the editable draft.  
**Long content:** expandable/collapsible without hiding it from screen readers incorrectly.

### 9. `CoachingProgress`

**Inputs:** real request lifecycle where available.  
**Contract:** no fabricated backend milestones. Static wording may describe broad local stages while the request is pending, but must not falsely claim a server event completed.  
**Accessibility:** one polite live region; no repeated announcement loop.

### 10. `CoachingReview`

**Inputs:** current response contract.  
**Children:** bottom line, practice signal, strengths, improvements, framework map, dimensions, relevant evidence, actions.  
**Contract:** optional/missing response fields collapse gracefully; no blank cards.

### 11. `PracticeSignal`

**Inputs:** score and existing label.  
**Contract:** includes `not an employer prediction`; color never carries meaning alone.

### 12. `ImproveComparison`

**Inputs:** original submitted answer, improved draft, change summary, grounding/source note.  
**Contract:** original is preserved; improved is editable; applying uses existing behavior; no publication/save implication.  
**Mobile:** tabs/stacking preserve both texts and accessible names.

### 13. `FailureRecovery`

**Inputs:** current error, preserved answer status, retry availability.  
**Actions:** Keep editing; Retry coaching.  
**Contract:** error replaces the pending review location; no page reset; no partial/fabricated review.

### 14. `MobileActionDock`

**Inputs:** state-specific primary/secondary actions.  
**Ready/drafting:** optional dictation, Up Next, Review My Answer.  
**Listening:** Stop, Up Next, Review My Answer.  
**Review:** dominant Improve Answer; other actions remain in content if space permits.  
**Improve:** dominant Use This Draft.  
**Contract:** accounts for safe area and virtual keyboard; page has bottom padding equal to dock height; no content is covered.

### 15. `TruthDisclosure`

**Inputs:** context-specific privacy/storage/media truth.  
**Contract:** concise truth near action; longer explanation behind disclosure. Never remove legally/product-critical truth merely to reduce density.

## Recommended state hooks

Use the existing state model. If scoped DOM hooks are needed, prefer descriptive data attributes such as:

```html
<main
  data-interview-mode="me"
  data-interview-state="drafting"
  data-dictation-state="idle"
  data-queue-state="closed"
>
```

Do not create a second JavaScript state machine solely to drive CSS. State hooks should reflect existing application state.

## CSS organization

- Scope under the Interview Studio route root.
- Map new visual values to existing theme tokens first.
- Keep component/state selectors predictable.
- Avoid `!important` except where repository conventions explicitly require it.
- Avoid broad element selectors that can affect other pages.
- Use logical properties where practical.
- Ensure flex/grid children have `min-width: 0` / `min-height: 0` where needed.
- Avoid nested independent vertical scroll areas in ordinary Interview Me states.
