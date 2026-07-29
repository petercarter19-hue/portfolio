# 04 — Information Architecture and Layout

## Architecture overview

The active Studio is a focused application surface composed of five layers:

1. **Existing PeerSlate global shell** — unchanged implementation.
2. **Studio identity and mode layer** — page title, public-demo truth, practice modes, History destination.
3. **Session summary layer** — concise current setup and Edit Session.
4. **Focus workspace** — main current-state stage plus contextual rail/drawer.
5. **Responsive action layer** — integrated composer footer on desktop; sticky action dock on mobile.

Do not build a long sequence of equal sections. Build one stage whose contents change with the current state.

## Existing shell

- Reuse the real header and secondary navigation partial/component.
- Do not reproduce the header from the mockup image.
- Scope Studio-specific styles under the existing route root or a new local root attribute such as `[data-interview-studio-ui="focus-v1"]` if that fits repository conventions.
- No Studio selector may unintentionally restyle other pages.

## Studio identity layer

### Desktop

- Pure white, quiet canvas across the body.
- Left: eyebrow `PUBLIC PRACTICE · BROWSER-LOCAL`, `Interview Studio`, one-line product promise.
- Right: compact public-demo identity chip and separate History destination.
- Below: three practice-mode cards aligned left:
  - Interview Me — `You answer. PeerSlate coaches.`
  - Interview AI — `You ask. AI answers.`
  - Video Practice — `Rehearse locally on camera.`
- Active mode uses a cobalt-blue edge/underline and a pale cool-blue tint; inactive modes remain calm white/navy surfaces.
- History must not look like a fourth practice method.

### Mobile

- Compact brand header from existing site.
- Studio title and concise demo label.
- Mode controls fit one row through compact labels/scrolling without shrinking text below readability.
- History may become an icon destination with a full accessible label.

## Session summary layer

- One full-width, low-height strip.
- Show current values, not a second configuration form.
- Recommended desktop copy pattern:
  `Experienced · Behavioral · 5-question mock`
- `Edit session` is the right-aligned action.
- Mobile may compress the same information to one line and place Edit at the end.
- Opening settings uses the existing configuration controls and confirmation behavior.

## Focus workspace — desktop

### Target geometry at 1536 × 1024

Use the mockup as visual authority. The prototype's measurable target is approximately:

- content max width: 1440px;
- body horizontal padding: about 30px at the target viewport;
- workspace grid: `minmax(0, 1fr) 292px`;
- grid gap: about 12–16px;
- main stage radius: 16–18px;
- rail card radius: 13–15px;
- stage padding: about 18–20px;
- stage and rail should fill the remaining viewport height without forcing the primary controls below the first viewport.

These are target relationships, not permission to hardcode one viewport. Use fluid sizing, `minmax()`, `clamp()`, flex/grid min-size corrections, and `100dvh` where appropriate.

### First-viewport requirement

At both 1440 × 900 and 1366 × 768, the user must see without scrolling:

- current question and progress;
- question metadata;
- interviewer-intent line;
- meaningful portion of the answer field;
- microphone/dictation action;
- save status/word count;
- enabled or disabled primary coaching action;
- concise privacy/submission truth.

If the global shell consumes more height than the prototype, reduce nonessential vertical whitespace before shrinking the question or hiding controls.

## Ready/drafting stage

Order:

1. progress row: `Question 1 of 5 · 20% complete`, one progress bar, state pill `Drafting`;
2. question in large editorial serif type;
3. metadata chips: family, competency, framework, expected speaking time;
4. one concise interviewer-intent strip;
5. answer composer;
6. concise submission truth;
7. quiet New Question action.

### Composer

The composer is the center of the experience.

- Real `<textarea>` remains the input source of truth.
- Label appears inside the composer top edge.
- Text area grows within sensible limits; it must not create nested-scroll confusion for ordinary answers.
- Desktop footer is attached to the composer and contains:
  - optional Use dictation / listening control;
  - live status or waveform when active;
  - stop control when active;
  - saved status;
  - word count;
  - dominant Review My Answer action.
- Do not place `Heard so far` in a detached transcript box. Dictated words appear in the same editable answer.

## Context rail

The rail changes with the state. It is contextual support, not a permanent dashboard.

### Ready

- Session summary.
- `Up next · 4 questions` disclosure.
- `Need a nudge?` disclosure.
- concise privacy card and optional detailed explanation link.

### Answering / queue open

- Queue becomes the rail's primary content.
- Current question remains in the main stage as a compact sticky summary.
- Each queued item shows number, question, and competency.
- Add-your-own-question action stays at the bottom.
- Closing the rail restores focus to the opener and preserves the answer.

### Processing

- Session/queue/privacy remain quiet.
- Do not show empty score or future feedback.

### Review

- Current question/attempt/practice-signal summary.
- `What happens next` explanation.
- browser-local truth.

### Improve

- Original preserved / improved editable / public no-change status.
- grounding boundary.

### Video

- device status;
- recording state, elapsed time, upload = none;
- what happens after stop.

### History

- browser-local summary;
- storage truth.

## Processing stage

- Compact question summary at top.
- Preserved submitted answer immediately below.
- In-place processing panel in the area where the review will appear.
- Step sequence uses actual request state where available:
  - answer received;
  - reviewing structure/relevance;
  - checking rubric;
  - preparing coaching.
- Never navigate to a blank loading page or hide the submitted answer.

## Review stage

Order:

1. compact question summary;
2. submitted answer available for context;
3. bottom-line review statement;
4. compact practice score with disclaimer;
5. What worked and Improve next in balanced panels;
6. STAR/framework completeness;
7. scoring dimensions and relevant proof/history when available;
8. actions: Try Again, Next Question, dominant Improve Answer.

The score is useful but must not visually overpower the coaching message.

## Improve stage

### Desktop

- Compact question summary.
- Heading: `Keep your voice. Strengthen the proof.`
- Original answer left; editable improved draft right.
- Original visibly preserved and unchanged.
- Improved draft visibly editable and not submitted/applied.
- `What changed` summary below, using existing coach response data only.
- Actions at bottom: Back to Feedback, Retry Out Loud, dominant Use This Draft.

### Mobile

- Do not squeeze two columns.
- Use stacked panels or an accessible Original / Improved segmented switch.
- Keep status labels and grounding truth visible.
- Primary action remains reachable in the bottom dock.

## Interview AI

- Use the same page/mode/session shell.
- Question input and Speak action form one compact request row.
- Answer basis options live in the context rail on desktop and a drawer/sheet on mobile.
- Generated answer occupies the main stage.
- Source labeling, why-it-works, relevant history, follow-up, Practice This Answer, and Compare behavior remain.

## Video Practice

- Use the same compact question summary.
- Local camera preview/recording stage dominates.
- Local-only label and timer are overlaid/adjacent without blocking preview.
- Stop and discard are clear.
- Device state and upload = none remain visible.
- Transcript coaching may appear below or in the same state according to current behavior; do not imply video analysis.

## History

- Treat as a separate destination with the same shell.
- Page title: practice on this device/browser.
- Filters and Start Interview Me near the top.
- Attempts list first, then goal/focus summary.
- Browser-only status visible without repeating paragraphs everywhere.
- Empty state uses real current behavior and never fabricates sessions.
