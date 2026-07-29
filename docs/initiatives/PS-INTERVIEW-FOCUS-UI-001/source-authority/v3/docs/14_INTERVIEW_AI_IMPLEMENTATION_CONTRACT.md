# 14 — Interview AI Complete Implementation Contract

## Purpose

Interview AI is not a chatbot. It is a structured, evidence-labeled interview-answer workspace that helps a user understand three different answer bases:

1. an illustrative best-practice response;
2. a response grounded only in the selected public profile's approved history;
3. a comparison of those approaches.

The UI update must make that distinction easier to understand without changing generation, grounding, source, follow-up, or transfer behavior.

## Authority

- `references/authoritative_mockups/06_interview_ai_light.png` controls desktop geometry, visual hierarchy, and the relationship between the question composer, answer workspace, basis selector, truth boundary, and actions.
- This document controls all additional Interview AI states not pictured in Screen 06.
- Existing repository behavior controls routes, values, requests, response fields, defaults, retries, transfer behavior, and data truth.

If the mockup or this document conflicts with proven released behavior, preserve behavior and document the presentation adaptation. Do not invent backend changes.

## Required desktop composition

### Shared shell

Use the exact shared Interview Studio shell, mode selector, session summary, white foundation, and contextual-rail proportions established by Screen 01.

### Main stage

1. Compact mode/state heading.
2. Question composer at the top.
3. Generated answer workspace below, replacing—not stacking under—empty/loading/error/result states.
4. Result actions attached to the bottom of the workspace.

### Context rail

1. `Answer basis` radio group.
2. Concise description of the selected basis.
3. Grounding/public-demo truth boundary.
4. Generation status or recoverable error when relevant.

Do not place the basis control far below the question or hide the selected basis after generation.

## Question composer

- The real question input is the source of truth.
- Typing is the default path.
- Optional Dictate writes into the same question input.
- `Get Answer` remains the one primary action before generation.
- Validation, limits, keyboard shortcut, and request trigger use current implementation.
- Loading the mode may not request microphone permission.
- A microphone failure returns focus to the input and leaves the full question intact.

## Answer-basis selector

Use actual radio-group semantics with one selected option.

### Best-practice example

- Label visibly as illustrative.
- Do not present the story as the profile owner's real experience.
- Result should emphasize structure and why the answer works.

### Approved public history

- Label visibly as grounded in approved public history/profile sources only.
- Do not imply access to private Slate records, account history, or unpublished material.
- Evidence/history shown must correspond to real approved sources returned or available through current behavior.

### Compare

- Clearly distinguish the two bases.
- Show structural differences without implying either answer predicts employer outcomes.
- Avoid three equal dense columns. Prefer answer-first content with a scannable comparison block or tabs/disclosures that maintain source labels.

## State contract

### AI empty

Show:

- question input;
- basis selector;
- concise example/help text;
- one primary `Get Answer` action;
- a calm empty workspace message explaining what will appear.

Do not show fake answer cards, empty source lists, follow-up input, or disabled comparison panels as if populated.

### Question drafting

- Preserve basis selection.
- Update validation/character status quietly.
- Optional Dictate remains secondary.
- `Get Answer` enablement follows current rules.

### Generating

- Keep the complete question and selected basis visible.
- Lock only controls that current behavior must lock.
- Use an in-place progress/skeleton state in the answer workspace.
- Announce generation once; do not create a full-screen spinner.
- Preserve a safe cancel/retry behavior only if currently supported.

### Answer ready — best practice

Order:

1. illustrative source label;
2. generated answer;
3. why this answer works/structural reasoning;
4. structural lessons or comparison aid, if real;
5. actions.

### Answer ready — approved public history

Order:

1. approved-public-history label;
2. generated answer;
3. why this answer works/reasoning;
4. relevant public history/sources used;
5. verification reminder;
6. actions.

### Answer ready — compare

Order:

1. compare label and concise explanation;
2. clearly labeled outputs or differences;
3. structural lessons;
4. evidence/source boundary;
5. actions.

### No grounding available

- State that the requested public-history answer could not be grounded with available approved evidence.
- Preserve the question.
- Offer a real existing recovery path: adjust question, choose best practice, retry, or new question as supported.
- Do not fill gaps with invented experience.

### Generation failure

- Preserve question and basis.
- Display the error where the result would appear.
- One primary retry action and a secondary edit/new-question action according to current behavior.
- Never clear a valid question merely because the request failed.

### Follow-up

- Hidden until a first answer exists if that is current behavior.
- Keep the original answer and grounding context available.
- Follow-up question input is type-first; optional dictation only if already supported.
- Ask action remains explicit.
- Follow-up result is clearly associated with the same evidence basis.
- Failure preserves both the first answer and follow-up question.

### Practice This Answer

- Remains the primary forward action after a useful result when current behavior supports it.
- Use existing transfer behavior to Interview Me.
- If the destination draft is nonempty and current settings require confirmation, preserve that safeguard.
- Never silently accept, publish, or store the AI text beyond current behavior.

### New Question

- Uses existing reset behavior.
- Do not clear session configuration or unrelated browser-local history.
- Restore logical focus to the question input.

## Mobile and tablet

- The main stage becomes one column.
- Question composer stays near the top.
- Answer basis becomes a compact horizontal control, drawer, or bottom sheet with the selected basis always visible.
- Generated answer appears before detailed reasoning/evidence.
- Evidence/source details may collapse but remain accessible.
- Primary result action stays reachable without covering text or the on-screen keyboard.
- Long generated answers, long evidence lists, and compare content must not cause horizontal page scrolling.

## Accessibility

- Answer basis uses radio-group semantics and a visible legend.
- Generation status uses a polite live region; failures use an appropriate alert without repeated announcements.
- On successful generation, move focus only if repository patterns support it; otherwise announce and provide a clear heading/skip target.
- Source labels are textual and not dependent on color.
- Collapsed evidence controls expose state with `aria-expanded` or the stack's equivalent.
- Keyboard users can reach question, basis, Get Answer, result, evidence, follow-up, and actions in logical order.

## Prohibited redesigns

- Generic assistant chat bubbles as the main architecture.
- A continuous unconstrained conversation that bypasses existing answer/follow-up contracts.
- Hidden source basis.
- Unlabeled blending of best-practice and profile-grounded content.
- Private-history or account-data claims.
- Automatic generation on every keystroke.
- Silent transfer into Interview Me.
- New AI prompts, scores, grounding sources, or backend calls.

## Interview AI acceptance checklist

- [ ] All three released answer bases remain present and semantically unchanged.
- [ ] Typing completes the whole question/generation path without a microphone.
- [ ] Dictation is optional and writes into the same question input.
- [ ] Question and selected basis survive loading and failure.
- [ ] Every result is visibly source-labeled.
- [ ] Public-history evidence is approved and truthful.
- [ ] Compare remains understandable on desktop and mobile.
- [ ] Follow-up preserves the same grounding.
- [ ] Practice This Answer uses existing safe transfer behavior.
- [ ] No generic-chat replacement or backend change.
