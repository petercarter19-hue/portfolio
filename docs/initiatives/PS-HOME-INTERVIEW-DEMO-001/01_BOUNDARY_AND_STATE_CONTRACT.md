# PS-HOME-INTERVIEW-DEMO-001 — Boundary and State Contract

This contract pins the deterministic behavior, exact fixed content, DOM
ownership, and truth boundary of the homepage Interview Studio scene.
Implementation must not deviate from this file without a recorded manager
decision.

## Amendment — 2026-07-19b (interaction: inline → pop-out modal)

Owner direction (Pete, 2026-07-19): the walkthrough must feel like the Voice
hero's "Talk about what happened" flow — a **modal that pops out over a
dimmed, blurred backdrop and walks through the steps** — for continuity.

The interaction model below therefore changes from an inline in-page panel
swap to a modal walkthrough. **Everything else in this contract is unchanged:**
all pinned fixed copy (§2), the no-input/no-request/no-storage truth boundary
(§3), reduced motion (§6), and the identity/attribution boundary (§7) all still
bind exactly as written.

What changes:

- The scene renders an on-page **poster** (kicker, title, the question as a
  quoted preview, the listening line, a persistent truth bar) plus one primary
  **"Walk me through it"** button (`data-int-open`, JS-gated).
- Clicking it opens a **modal dialog** (`role="dialog"`, `aria-modal="true"`,
  labelled by its title) that contains the four steps. It pops out over a
  full-viewport dimmed + blurred backdrop, matching the Voice overlay's visual
  language (backdrop `rgb(8 18 37 / 42%)` + `blur(8px)`, white card, serif
  title, step rail, sticky truth strip in the footer, Back / Next, and — on
  step 4 — a normal Interview Studio link).
- The four steps are still **server-rendered** inside the modal; steps 2–4
  ship `hidden`; JS only opens/closes the modal and toggles the visible step.
- The modal is **portaled to `<body>`** on init (inside a `home-v3` wrapper so
  the design-system classes and `--hv-*` tokens still resolve) because the
  homepage's `main.main-content` sets `isolation: isolate`, which would
  otherwise trap a fixed overlay below the sticky global header. This mirrors
  the repository's known modal-stacking guidance.
- **No-JS behavior (revised):** the poster (question + truth bar) is always
  server-rendered and visible; the "Walk me through it" button is hidden
  (JS-gated) and a normal **"Open Interview Studio"** link (`.hv-int-nojs`) is
  shown instead. The modal never opens without JS. Essential truth still lives
  in server HTML in every scenario.
- Focus: opening moves focus into the modal (step-1 heading); focus is trapped
  (Tab cycles within the modal); Escape, the close button, and a backdrop click
  all close it and restore focus to the trigger. Each step change moves focus
  to the new step's heading and announces once via the live region.

Sections §1, §4, and §5 below describe the original inline model and are
retained as history; where they conflict with this amendment, the amendment
controls.

## 1. The four deterministic states

The scene is a fixed, client-side walkthrough with exactly four states.
Content never varies by visitor, time, input, or network. There is no fifth
state, no loading state, and no error state — nothing is requested, so nothing
can fail to load.

| # | State id | State name | Advance control (primary action) |
|---|---|---|---|
| 1 | `q` | Question | `Show illustrative answer` (button) |
| 2 | `a` | Sample answer | `Submit sample answer` (button) |
| 3 | `r` | Coaching review | `Show improved retry` (button) |
| 4 | `t` | Improved retry | `Practice this question in Interview Studio` (normal link to the real route) |

- Exactly one state panel is visible at a time; the other three carry the
  `hidden` attribute.
- Server-rendered initial state is **State 1**; panels 2–4 ship with `hidden`
  already present in the HTML (not applied by JS).
- The four step-rail controls are always operable in both directions
  (fixed fictional content — there is nothing to protect by locking steps).
- State transitions are instant DOM swaps (`hidden` toggling). Any decorative
  transition lives in CSS behind `prefers-reduced-motion: no-preference`.

## 2. Exact fixed content (pinned strings)

All strings below are final. The two owner-required copy corrections are
already applied (§2.8). Typographic entities (é, —, ’) follow the existing
homepage partials' conventions.

### 2.1 Editorial column (left rail, all states)

- Eyebrow: `Homepage scene · Interview Studio`
- H2 (scene title, `id="hv-interview-title"`): `Practice how your experience sounds.`
- Lede: `Voice first. Text always available. One realistic question, clear coaching, and one stronger retry.`
- Badge: `Illustrative walkthrough`
- Truth checklist (three items):
  1. `Fictional answer—not Pete’s and not the visitor’s.`
  2. `No microphone, AI request, draft, attempt, history, or media storage.`
  3. `The final action opens the real public Interview Studio.`
- Sequence note (correction applied): `Placed after Living Résumé and before My Story/Future so the homepage moves from capture, to presentation, to practice, to what comes next.`

### 2.2 Ledger card header (all states)

- Kicker: `Interview Studio · Illustrative walkthrough`
- H3: `Answer → understand → improve`
- Step counter (updates per state): `Step 1 of 4` … `Step 4 of 4`
- Step rail labels: `Question`, `Sample answer`, `Coaching review`, `Improved retry`

### 2.3 State 1 — Question

- Chips: `Behavioral`, `Leadership`, `Recommended: STAR`; meta: `Approx. 2 minutes`
- H4 (focus target): `Tell me about a time you led a team through a major change.`
- Listening line: `What the interviewer is listening for: clear ownership, communication through resistance, and a measurable result.`
- Answer-method switch: `Voice` (selected, tagged `Default`) and `Text` (see §4.4)
- Voice explanation panel: heading `Voice is front and center in the real Studio.`
  body `Speak naturally, review the transcript, or switch to text before submitting. This homepage walkthrough does not activate the microphone.`
- Text explanation panel (shown only when Text is toggled): heading
  `Text is a first-class way to answer.` body `Type instead of speaking—both
  methods edit the same single answer and share one explicit Submit answer
  step in the real Studio. This homepage walkthrough does not accept typing.`
- Inline note: `Illustrative only. The next state reveals a fixed fictional answer. No visitor response is captured.`
- Footer note: `Step 1 of 4. One realistic question. No input, storage, or AI request on the homepage.`

### 2.4 State 2 — Sample answer

- Chips: `Illustrative voice transcript`, `Fictional example`; meta: `Sample only`
- H4 (focus target): `A clear beginning—with one result still missing.`
- Transcript label: `Fictional sample answer`
- Fixed fictional transcript:
  `During a major schedule change, I brought engineering, program management, and test together around one recovery plan. We met twice a week, tracked decisions visibly, and escalated only the issues that threatened the critical path. The team completed the transition without missing the delivery, but I would make the measurable result more explicit.`
- The static waveform block is decorative (`aria-hidden="true"`), labeled
  `Illustrative voice` visually.
- Footer note: `Real Studio action shown: Voice and text both lead to one explicit Submit answer step. Here, the button reveals predetermined coaching only.`

### 2.5 State 3 — Coaching review

- H4 (focus target, bottom line): `Strong ownership and clear coordination. The result needs one sharper measure.`
- Bottom-line body: `The fictional answer explains the change and leadership actions well. Its ending describes success, but does not yet make the impact specific enough.`
- `What worked`: `Clear situation and leadership role` · `Specific coordination actions` · `Calm explanation of escalation`
- `Improve next`: `Name the resistance or tradeoff` · `Quantify the delivery impact` · `Close with what changed afterward`
- STAR tiles: `S — Situation clear` (complete), `T — Task clear` (complete),
  `A — Actions specific` (complete), `R — Strengthen result` (improvement target)
- Footer note: `Fixed walkthrough coaching. No AI request or profile history is used.`

### 2.6 State 4 — Improved retry

- Chips: `Retry strengthened`, `Result made specific`; meta: `Illustrative retry`
- H4 (focus target): `Same experience. Stronger ending. Still the speaker’s voice.`
- `Original sample` panel: the identical State 2 transcript, repeated verbatim.
- `Improved retry` panel (correction applied):
  `During a major schedule change, I brought engineering, program management, and test together around one recovery plan. I set twice-weekly decision reviews, made ownership visible, and escalated only issues that threatened the critical path.`
  then, as the highlighted material change:
  `That alignment kept the transition on schedule and avoided a delivery slip.`
- Change tiles: `Clearer result — Names the avoided delivery slip.` ·
  `Stronger impact — Ties the gain to the delivery.` ·
  `Voice preserved — Refines rather than replaces.`
- Footer note: `Ready for real practice. Open the full public Studio to answer by voice or text and submit for real coaching.`
- Final action: normal link, `Practice this question in Interview Studio`,
  `href="{{ url_for('interview_studio') }}"`.

### 2.7 Persistent truth bar (all states, all breakpoints)

`Fictional example` · `No visitor input` · `No AI request` · `Nothing stored`

The truth bar is part of the card footer, rendered in server HTML, and is never
hidden at any breakpoint, zoom level, or state (this corrects the design
source, which hid it in mobile landscape).

### 2.8 Copy corrections applied (owner-required)

1. The design source's sequence note said "from capture, to proof, to
   practice." Site Rules deprecate user-facing "proof" language; the pinned
   string in §2.1 uses **"capture, to presentation, to practice."**
2. The design source's improved retry claimed the team gained "a repeatable
   review process for the next phase," a fact never established in the
   fictional original. The pinned retry in §2.6 **removes** that claim (chosen
   over seeding it into the original, to keep the original's one weakness —
   an unspecific result — clean and legible). The second change tile is
   reworded accordingly.

## 3. No-input / no-request / no-storage boundary

### 3.1 Prohibited APIs and patterns

`static/js/homepage-interview-demo.js` and the scene partial must contain none
of the following, and tests assert their absence (see
[03_ACCESSIBILITY_AND_VALIDATION_PLAN.md](03_ACCESSIBILITY_AND_VALIDATION_PLAN.md) §3):

- Network: `fetch(`, `XMLHttpRequest`, `sendBeacon`, `WebSocket`, `EventSource`,
  dynamic `import(`, script injection.
- Storage: `localStorage`, `sessionStorage`, `indexedDB`, `document.cookie`,
  Cache API, File System Access API.
- Media/input: `getUserMedia`, `mediaDevices`, `MediaRecorder`,
  `SpeechRecognition`/`webkitSpeechRecognition`, `AudioContext`.
- Forms: the partial contains no `<form>`, `<textarea>`, or `<input>` element.
  The answer-method switch and walkthrough controls are `<button type="button">`
  elements; the final CTA is an `<a>`.

### 3.2 What the scene may do

- Toggle the `hidden` attribute on its own four state panels.
- Toggle classes/ARIA attributes on its own step rail, method switch, and root.
- Set `textContent` of its own live region.
- Call `.focus()` on its own state headings.
- Read `matchMedia('(prefers-reduced-motion: reduce)')` if needed (CSS-first is
  preferred; JS must not animate).

The script must scope every query to the scene root
(`[data-home-interview-demo]`) and must not touch any DOM outside it.

## 4. DOM and JavaScript state ownership

### 4.1 DOM contract (server-rendered by the partial)

```
section.hv-interview[data-home-interview-demo][aria-labelledby="hv-interview-title"]
├─ div.site-container.hv-interview__inner
│  ├─ div.hv-interview__copy          (editorial column §2.1; static)
│  └─ article.hv-int-sheet            (ledger card)
│     ├─ header.hv-int-sheet__head
│     │  ├─ kicker + h3 + step counter (span[data-int-count])
│     │  └─ ol.hv-int-steps           (4× li > button[type=button][data-int-step="1..4"])
│     ├─ p.hv-visually-hidden[role="status"][data-int-live]   (live region, empty at load)
│     ├─ div.hv-int-body
│     │  ├─ section[data-int-state="1"] > h4[tabindex="-1"] …  (visible at load)
│     │  ├─ section[data-int-state="2"][hidden] > h4[tabindex="-1"] …
│     │  ├─ section[data-int-state="3"][hidden] > h4[tabindex="-1"] …
│     │  └─ section[data-int-state="4"][hidden] > h4[tabindex="-1"] …
│     ├─ div.hv-int-nojs              (no-JS fallback §5; hidden when JS active)
│     └─ footer.hv-int-truthbar       (§2.7; always visible)
```

- Step-rail buttons: the current step's button carries `aria-current="step"`.
  Completed steps get `data-done="true"` plus a visually-hidden ` (completed)`
  suffix in their accessible name. Server HTML ships step 1 as current.
- Advance buttons live inside their state panel's footer row and carry
  `data-int-go="2|3|4"`.
- The State 4 CTA is a plain anchor; JS never intercepts it.
- The answer-method switch (states 1–2) is a group of two
  `<button type="button" data-int-method="voice|text" aria-pressed="true|false">`;
  Voice ships pressed in server HTML.

### 4.2 JavaScript state model

- Single module-scope integer `current` (1–4), initialized from the DOM
  (the panel without `hidden`), not from any stored value.
- One public transition `go(n)`:
  1. bounds-check `n` (1–4; no-op if `n === current`);
  2. hide the old panel, unhide the new (toggle `hidden` only);
  3. update step-rail `aria-current` / `data-done` and the step counter text;
  4. set the live region: `Step {n} of 4: {state name}` (single assignment —
     announced once);
  5. if the transition was keyboard-triggered (§4.3), move focus to the new
     panel's `h4[tabindex="-1"]`.
- Method toggle `setMethod('voice'|'text')`: flips `aria-pressed` and swaps the
  two explanation panels in State 1 (and the one-line caption in State 2).
  It changes explanatory presentation only; the fixed transcript never changes.
- Init: add `hv-int--js` class to the scene root (reveals interactive controls,
  hides the no-JS fallback), bind click/keydown listeners via event delegation
  on the sheet, guard against double-init. No timers, no observers, no
  animation frames.

### 4.3 Focus movement and announcements

- **Modality detection:** a `pointerdown` listener on the sheet sets a flag
  cleared on the next `click`. Activation without a preceding `pointerdown`
  is keyboard-triggered.
- **Keyboard-triggered transition:** focus moves to the new state's
  `h4[tabindex="-1"]` (which has a visible focus outline). Pointer-triggered
  transitions do not steal focus; the live region still announces.
- **Announcement:** exactly one `role="status"` live region per scene; each
  transition writes one string; no other live regions, no repeated
  announcements, no announcement on initial load.
- The step-rail buttons and advance buttons are native buttons — Enter and
  Space work without extra key handling.

### 4.4 Answer-method switch honesty

The Voice/Text controls are real toggles (not dead controls, matching the
homepage's established rule against fake tabs): they switch which input-method
explanation is shown. They never enable input, never activate a microphone,
and never alter the fixed fictional content. Voice is the default-pressed
method per the voice-first addendum; Text is a peer, never hidden.

## 5. No-JavaScript behavior

With JavaScript unavailable:

- The server HTML already shows State 1: the question, chips, listening line,
  method explanation, editorial column, and truth bar — all truthful with no
  dead ends.
- The step rail, advance buttons, and method switch are hidden by CSS
  (`.hv-interview:not(.hv-int--js) .hv-int-controls { display: none }`) so no
  dead controls are exposed.
- The `hv-int-nojs` panel is visible (CSS hides it only under `.hv-int--js`)
  and reads: `JavaScript is unavailable, so the walkthrough stays on this
  step. The real Interview Studio works without it—` followed by a normal
  link `Open Interview Studio` (`url_for('interview_studio')`).
- No `<noscript>` element is required; the class-gating pattern covers both
  "JS disabled" and "JS failed to load."
- Essential truth (fictional example, no input/no storage, real-route link)
  is therefore present in server-rendered HTML in every scenario.

## 6. Reduced motion

Per the design authority's reduced-motion guidance:

- All scene transitions are instant DOM swaps; CSS may add a subtle fade/slide
  **only** inside `@media (prefers-reduced-motion: no-preference)`.
- No pulsing microphone, no animated waveform (the waveform is a static
  decorative graphic in all modes), no shimmer, no count-up numbers.
- Focus movement and single announcements behave identically with reduced
  motion; the four step controls remain available for direct movement.

## 7. Identity and attribution boundary

- The fictional sample answer is attributed to no one. The scene never uses
  Pete's name, photo, role, or history inside the walkthrough content.
- The scene claims no signed-in state, account, private history, cloud
  persistence, billing, entitlement, Interview Story, or delivery analytics.
- Voice-first emphasis is presentation of the real Studio's input model, with
  the explicit statement that the homepage does not activate a microphone.
