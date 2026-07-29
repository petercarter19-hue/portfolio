# 07 — White Visual System, Responsive, Theme, and Accessibility Specification

## Breakpoint strategy

Use the repository's existing breakpoint system where possible. The following are outcome requirements, not a mandate to add these exact media queries.

### Wide desktop — approximately 1200px and above

- Two-column workspace: fluid main stage + 280–320px contextual rail.
- Three practice-mode cards aligned left; separate History destination right.
- Composer footer contains optional dictation, save/word status, and the primary action; the textarea remains visually dominant.
- Review uses balanced panels; Improve uses side-by-side comparison.

### Compact desktop/tablet landscape — approximately 900–1199px

- Maintain two columns only while the main answer stage remains comfortable.
- Rail may narrow, collapse behind a button, or move below based on actual available width.
- Never shrink the question/composer merely to preserve an always-open rail.
- Primary action remains adjacent to the composer.

### Tablet portrait / 200% reflow — approximately 700–899px effective width

- Single-column main stage.
- Context rail becomes accessible accordion/drawer/bottom sheet.
- Session summary remains one concise row or wraps cleanly.
- Review panels may stack.
- Improve comparison stacks or uses a segmented view.

### Mobile — 320–699px

- Single-column stage.
- Question full in ready state; compact sticky question summary after the user scrolls or begins a long answer.
- No right rail.
- Up Next, nudge, settings, privacy detail, and answer basis use bottom sheets/drawers.
- Fixed bottom action dock with safe-area padding.
- Body/stage bottom padding prevents the dock from covering content.
- Virtual keyboard does not hide the focused textarea line or primary action.

## Required viewport matrix

Capture and validate at minimum:

- 1536 × 1024 — visual-authority desktop;
- 1440 × 900 — common desktop;
- 1366 × 768 — constrained-height desktop;
- 1024 × 768 — tablet landscape / compact desktop;
- 834 × 1194 — tablet portrait;
- 844 × 390 — mobile landscape;
- 390 × 844 — controlling mobile portrait;
- 320 × 568 — minimum narrow/short stress case;
- desktop browser at 200% zoom.

## Mobile action dock

- Minimum control target: 44 × 44 CSS px; prefer 48px for mic/primary actions.
- Includes safe-area inset.
- Ready: mic, Up Next count, Review My Answer.
- Listening: stop, Up Next, Review My Answer.
- Review: dominant Improve Answer; Try Again/Next remain reachable in content or secondary sheet.
- Improve: dominant Use This Draft.
- Dock may not overlap browser permission prompts, bottom sheets, or focused fields.

## Question continuity

- At desktop, the question remains in the active stage header.
- When long content scrolls, a compact sticky summary may pin within the stage/top of viewport.
- On mobile, compact summary should identify question number and enough text to restore context.
- Avoid two independently focusable/read question headings.

## White light theme — controlling owner decision

The beige/ivory/gold direction is retired. Do not preserve it, interpolate toward it, or use it as a fallback. The approved light experience uses a **pure white page foundation**, cool supporting surfaces, deep navy text, cobalt-blue interaction emphasis, and restrained teal status accents.

Target character:

- pure white page canvas;
- white primary surfaces;
- pale cool-gray/blue supporting surfaces only where separation is needed;
- deep navy ink and headings;
- cobalt blue for selected modes, links, progress, focus, and primary actions;
- restrained teal for dictation/listening, success, saved status, and coaching-state accents;
- cool gray borders and low, neutral shadows;
- no beige, cream, ivory, tan, parchment, warm-gray wash, gold, or amber as a foundational or active-state color.

Prototype reference values must be mapped into existing repository tokens rather than duplicated blindly:

```css
--page-canvas: #ffffff;
--surface: #ffffff;
--surface-subtle: #f5f8fc;
--ink: #14233d;
--ink-strong: #102a4a;
--muted: #64748b;
--line: #dbe3ed;
--primary: #2563eb;
--primary-hover: #1d4ed8;
--primary-soft: #e8f0ff;
--teal: #0f766e;
--teal-soft: #e5f5f1;
--danger: #b42318;
--danger-soft: #feeceb;
--focus-ring: #60a5fa;
```

Required contrast checks for the reference values:

- `#14233d` on white: approximately 15.7:1;
- `#64748b` on white: approximately 4.76:1;
- white on `#2563eb`: approximately 5.17:1;
- `#102a4a` on `#f5f8fc`: approximately 13.58:1.

Do not force these exact hex values if the existing PeerSlate token system already provides an owner-approved equivalent with sufficient contrast. Preserve the **white/cool/cobalt** character.

## Dark theme

Dark mode relights the same DOM, geometry, state order, and interaction hierarchy. It is not a separate product and must not introduce different controls or content.

Reference values:

```css
--page-canvas: #07111f;
--surface: #0d1b2e;
--surface-subtle: #13243a;
--ink: #f8fafc;
--muted: #a8b4c7;
--line: #263b55;
--primary: #6ea8ff;
--primary-hover: #8ab4ff;
--primary-soft: #19365c;
--teal: #5eead4;
--teal-soft: #123c3c;
--danger: #fb7185;
--danger-soft: #3b1f2a;
```

Use the existing theme class/data mechanism and token names. Do not fork DOM or business logic by theme.

## Typography

Use current loaded PeerSlate fonts.

- Editorial serif/Newsreader (or existing accepted serif) for Studio title, question, bottom-line coaching statement, and key state headings.
- Inter/current sans for controls, metadata, answer text, status, feedback details, and rail.
- Question target: approximately 29–34px desktop, 24–29px mobile, with 1.1–1.2 line height.
- Body answer/feedback: do not fall below a readable 14–16px production size merely to fit a screenshot.
- Small labels should remain at least the repository's accessible minimum and high contrast.

## Accessibility requirements

### Semantics

- one `h1` for Interview Studio;
- logical heading hierarchy through question, review, and improve states;
- real links for navigation;
- real buttons for actions;
- textarea has persistent label and help association;
- progress has accessible current/maximum text;
- mode current state uses `aria-current` or appropriate tab semantics without breaking links.

### Keyboard

- complete operation without pointer;
- visible focus on every interactive element;
- Ctrl/Cmd+Enter submit remains if currently supported;
- Escape closes current drawer/dialog where appropriate;
- no keyboard trap;
- logical focus order matches visual order;
- sticky/fixed bars do not hide focus.

### Screen reader

- hidden inactive states are not announced;
- save/listening/processing status uses restrained live regions;
- current question and state are named;
- score includes text, not color alone;
- queue current item is identified;
- public-demo and browser-local truth remains available.

### Motion

Respect `prefers-reduced-motion`:

- no pulsing/glowing loop required to understand listening or processing;
- waveform may become a static status indicator;
- drawers use reduced/no animation;
- progress transitions are not essential.

### Contrast and non-color cues

- verify WCAG AA contrast for text and interactive states;
- active mode has border/shape/text cue in addition to color;
- success/error use icon and text;
- focus outline remains visible in both themes.

### Content stress

Test:

- long question;
- long competency label;
- 5,000-character answer or actual current maximum;
- multiline coaching bottom line;
- missing optional score detail;
- long improved draft;
- 30-question queue;
- browser zoom/reflow;
- system font fallback.

## No-JS and unavailable states

- The no-JS message and real links remain truthful.
- Local-storage blocked/unavailable state remains usable.
- Dictation unsupported/denied leaves typing fully functional.
- Camera/microphone denied leaves truthful recovery and transcript practice.
- AI/server failure preserves text and offers retry.
