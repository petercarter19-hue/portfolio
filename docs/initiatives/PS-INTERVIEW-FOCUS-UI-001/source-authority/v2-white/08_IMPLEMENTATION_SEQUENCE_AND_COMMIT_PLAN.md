# 08 — Implementation Sequence and Commit Plan

This sequence is designed to let Codex work against the real code without guessing, while keeping the change reviewable and reversible.

## Working model

- One dedicated branch/worktree.
- One writer for shared Interview Studio files.
- No production deploy or merge.
- Small, coherent commits.
- Run the relevant tests after every phase.
- Capture visual evidence as states become complete rather than waiting until the end.

## Phase 0 — Read-only discovery and baseline

Deliver before code:

- route/template/script/style/test map;
- current state diagram;
- endpoint/payload map;
- storage-key map;
- media lifecycle map;
- visual-shell reuse map;
- file ownership/conflict check;
- baseline test result;
- baseline screenshots at 1536×1024, 1366×768, and 390×844;
- implementation plan mapping each requirement to files.

No code changes in Ask mode.

## Phase 1 — Scoped foundation

Goal: establish the new composition without changing behavior.

- Reuse current global shell.
- Add/adjust a Studio-scoped root and theme token aliases if needed.
- Build Studio identity/mode/session layout.
- Build responsive workspace grid and contextual rail container.
- Preserve all existing links and controls.
- Do not yet move complex state logic.

Suggested commit:

`feat(interview-studio): establish focus-stage shell and scoped tokens`

Acceptance:

- neighboring pages unaffected;
- both themes render;
- all mode links/settings still operate;
- no backend diff.

## Phase 2 — Interview Me ready/drafting composer

- Move current question, progress, metadata, intent, textarea, dictation, save/word state, submit, privacy, New Question, Up Next, and optional example into the approved hierarchy.
- Make inactive future sections absent/hidden from the active accessibility tree.
- Use current textarea and handlers; do not duplicate them.
- Add first-viewport sizing and sticky question behavior.

Suggested commit:

`feat(interview-studio): center Interview Me question and answer composer`

Acceptance:

- typing/autosave/reload/word count/submission validation unchanged;
- question and controls visible at constrained desktop;
- no empty review/improve panels visible.

## Phase 3 — Dictation, queue, settings, and mobile action dock

- Integrate live dictation state into the same composer.
- Replace detached transcript presentation with the editable answer display while preserving actual recognition behavior.
- Implement contextual queue rail and responsive bottom sheet.
- Preserve custom question and draft-replacement confirmation.
- Implement mobile action dock and keyboard/safe-area handling.

Suggested commit:

`feat(interview-studio): integrate voice queue and mobile actions`

Acceptance:

- permission allow/deny/unavailable tested;
- no typed text loss;
- queue selection behavior unchanged;
- mobile keyboard does not cover actions.

## Phase 4 — Coaching processing and failure recovery

- Keep submitted answer visible.
- Render processing in place.
- Map current request lifecycle honestly.
- Render failure in the same result region with Keep editing and Retry coaching.
- Ensure one request and preserved answer.

Suggested commit:

`feat(interview-studio): keep coaching processing and recovery in context`

Acceptance:

- slow/success/error tested;
- no duplicate requests;
- no partial fake review;
- answer remains intact.

## Phase 5 — Coaching review

- Recompose existing review data into bottom-line-first hierarchy.
- Keep all current score, STAR, strengths, improvement, dimension, and relevant-history content.
- One dominant Improve Answer action.
- Preserve automatic browser-local history behavior.

Suggested commit:

`feat(interview-studio): refine coaching review hierarchy`

Acceptance:

- response fixtures with complete, partial-optional, and long content;
- retry/next/improve behavior unchanged;
- score disclaimer present.

## Phase 6 — Improve answer

- Original preserved and improved editable.
- Desktop comparison; mobile stack/tabs.
- Change summary uses real response data.
- Map Use This Draft and Retry Out Loud to existing functions only.

Suggested commit:

`feat(interview-studio): add focused improve-answer comparison`

Acceptance:

- no account save/publication implication;
- back/retry/use behavior unchanged;
- original cannot be silently overwritten.

## Phase 7 — Shared shell for Interview AI, Video Practice, and History

- Apply mode/session/surface hierarchy to existing destinations.
- Preserve all functions and truth boundaries.
- Do not broaden the redesign into new AI/media/history features.

Suggested commit:

`feat(interview-studio): align AI video and history with focus shell`

Acceptance:

- every existing mode and action tested;
- no media upload;
- all source labels/history warnings remain.

## Phase 8 — Dark parity, responsive, accessibility

- Same DOM/state/actions for dark.
- Complete tablet/mobile reflow.
- Focus management, live regions, reduced motion, zoom, contrast, long content.
- No state loss on theme change.

Suggested commit:

`fix(interview-studio): complete theme responsive and accessibility parity`

## Phase 9 — Regression, evidence, and closeout

- Full functional test matrix.
- Visual screenshots and overlay review against references.
- Console/network audit.
- No unexpected file or dependency changes.
- Technical and plain-English reports.

Suggested commit:

`test(interview-studio): add focus-stage regression and visual evidence`

## Guardrails during implementation

- Do not edit backend code to make UI tests easier.
- Do not alter API payloads or response shapes.
- Do not rename storage keys.
- Do not clear real developer browser data during automated tests; use isolated contexts.
- Do not add a second copy of current handlers.
- Do not leave old and new active UI simultaneously in the DOM.
- Do not add a framework dependency.
- Do not use global CSS resets.
- Do not commit generated secrets, `.env`, tokens, publish profiles, browser profile data, or local recordings.

## Rollback design

The branch should be reversible by reverting its focused commits. Avoid irreversible migrations or coupled backend changes. Keep Studio-specific styling scoped so rollback does not require repairing unrelated pages.
